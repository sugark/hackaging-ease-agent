#!/usr/bin/env python3
"""
DataPointExtractor for extracting clinical data from research articles.
Uses Google's Gemini API with context caching for efficient processing of PDF articles.

This script:
1. Reads _suggested_analysis.json for clinical test and cohort information
2. Uses system prompt constant from system_prompt_extract_datapoints.py
3. Reads _classified_articles.json to find candidate articles with PDFs
4. Uses Gemini to extract CSV data as suggested in system prompt
5. Saves results after each iteration to _extracted_datapoints.csv
"""

import json
import os
import io
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from dotenv import load_dotenv

from google import genai
from google.genai import types
from system_prompt_extract_datapoints import SYSTEM_PROMPT_EXTRACT_DATA_POINTS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataPointExtractor:
    def __init__(self):
        """
        Initialize the DataPoint Extractor.
        """
        self.client = genai.Client()
        self.model_name = "gemini-flash-latest"
        
        # Load suggested analysis information
        self.analysis_info = self._load_suggested_analysis()
        
        # Format system prompt with analysis information
        self.system_instruction = self._format_system_prompt()
        
        # Initialize CSV headers
        self.csv_headers = [
            "study_id", "author_year", "country", "population_type", "sample_size_intervention",
            "sample_size_control", "intervention_name", "dose_mg_per_day", "duration_days",
            "outcome_name", "biomarker_unit", "intervention_baseline_mean", "intervention_baseline_sd",
            "intervention_post_mean", "intervention_post_sd", "control_baseline_mean",
            "control_baseline_sd", "control_post_mean", "control_post_sd", "mean_difference",
            "sd_difference", "p_value", "effect_direction", "statistical_significance"
        ]
    
    def _load_suggested_analysis(self) -> Dict[str, Any]:
        """Load suggested analysis information from _suggested_analysis.json."""
        try:
            with open('_suggested_analysis.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("_suggested_analysis.json not found")
            return {
                "selected_clinical_test": "Unknown",
                "recommended_cohorts": []
            }
    
    def _format_system_prompt(self) -> str:
        """Format the system prompt constant with analysis information."""
        selected_clinical_test = self.analysis_info.get("selected_clinical_test", "Unknown")
        recommended_cohorts = "\n".join([f"- {cohort}" for cohort in self.analysis_info.get("recommended_cohorts", [])])
        
        formatted_prompt = SYSTEM_PROMPT_EXTRACT_DATA_POINTS.format(
            selected_clinical_test=selected_clinical_test,
            recommended_cohorts=recommended_cohorts
        )
        
        return formatted_prompt
    
    def load_classified_articles(self) -> Dict[str, Any]:
        """Load classified articles from _classified_articles.json."""
        try:
            with open('_classified_articles.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("_classified_articles.json not found")
            return {"articles": []}
    
    def get_candidate_articles_with_pdfs(self) -> List[Dict[str, Any]]:
        """
        Get all articles with pdf_path that have candidate_meta_analysis classification as CANDIDATE.
        """
        articles_data = self.load_classified_articles()
        articles = articles_data.get('articles', [])
        
        candidate_articles = []
        for article in articles:
            # Check if article has PDF path
            if not article.get('pdf_path') or not os.path.exists(article.get('pdf_path', '')):
                continue
                
            # Check if article has classifier results
            classifier_results = article.get('classifier_results', {})
            candidate_meta = classifier_results.get('candidate_meta_analysis', {})
            result = candidate_meta.get('result', {})
            
            # Check if candidacy_classification is CANDIDATE
            if result.get('candidacy_classification') == 'CANDIDATE':
                candidate_articles.append(article)
                logger.info(f"Found candidate article: {article.get('pmid', 'unknown')} - {article.get('title', 'No title')[:80]}...")
        
        logger.info(f"Found {len(candidate_articles)} candidate articles with PDFs")
        return candidate_articles
    
    def upload_pdf_file(self, pdf_path: str, pmid: str) -> Optional[Any]:
        """
        Upload a PDF file to Gemini API.
        
        Args:
            pdf_path: Path to the PDF file
            pmid: PubMed ID for identification
            
        Returns:
            Uploaded file object or None if failed
        """
        try:
            # Check if PDF file exists
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF file not found: {pdf_path}")
                return None
            
            # Upload the PDF file
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            doc_io = io.BytesIO(pdf_content)
            
            document = self.client.files.upload(
                file=doc_io,
                config=dict(mime_type='application/pdf')
            )
            
            logger.info(f"Uploaded PDF for article {pmid}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to upload PDF for {pmid}: {str(e)}")
            return None
    
    def extract_datapoints(self, document: Any, pmid: str) -> Optional[str]:
        """
        Extract datapoints using direct API call with uploaded document.
        
        Args:
            document: Uploaded document object
            pmid: PubMed ID for identification
            
        Returns:
            CSV data as string or None if failed
        """
        try:
            # Create the prompt combining system instruction and user request
            full_prompt = f"{self.system_instruction}\n\nExtract all clinical test related quantitative variables required for meta-analysis from this PDF document. Output MUST be CSV format only."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[full_prompt, document],
                config=types.GenerateContentConfig(
                    response_mime_type="text/plain"
                )
            )
            
            logger.info(f"Completed data extraction for {pmid}")
            return response.text
            
        except Exception as e:
            logger.error(f"Failed data extraction for {pmid}: {str(e)}")
            return None
    
    def save_to_csv(self, csv_data: str, pmid: str):
        """
        Save CSV data to _extracted_datapoints.csv, appending to existing file.
        
        Args:
            csv_data: CSV formatted string
            pmid: PubMed ID for logging
        """
        try:
            # Parse the CSV data
            lines = csv_data.strip().split('\n')
            if not lines:
                logger.warning(f"No data to save for {pmid}")
                return
            
            # Check if file exists to determine if we need to write headers
            file_exists = os.path.exists('_extracted_datapoints.csv')
            
            # Determine if first line is header and skip it for data processing
            data_lines = lines
            if lines and ('study_id' in lines[0].lower() or 'author_year' in lines[0].lower()):
                data_lines = lines[1:]  # Skip header line for data processing
            
            with open('_extracted_datapoints.csv', 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers only if file doesn't exist
                if not file_exists:
                    writer.writerow(self.csv_headers)
                
                # Write data rows, replacing study_id with pmid
                for line in data_lines:
                    if line.strip():  # Skip empty lines
                        # Handle potential commas in quoted fields
                        row_data = []
                        reader = csv.reader([line])
                        for row in reader:
                            row_data = row
                            break
                        if row_data:
                            # Replace study_id (first column) with pmid
                            if len(row_data) > 0:
                                row_data[0] = pmid
                            writer.writerow(row_data)
            
            logger.info(f"Saved extracted data for {pmid} to _extracted_datapoints.csv")
            
        except Exception as e:
            logger.error(f"Failed to save CSV data for {pmid}: {str(e)}")
    
    def process_single_article(self, article: Dict[str, Any]) -> bool:
        """
        Process a single article for data extraction.
        
        Args:
            article: Article data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pmid = article.get('pmid', 'unknown')
        pdf_path = article.get('pdf_path')
        
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning(f"No valid PDF for article {pmid}")
            return False
        
        logger.info(f"Processing article {pmid} for data extraction")
        
        # Upload PDF file
        document = self.upload_pdf_file(pdf_path, pmid)
        if not document:
            logger.error(f"Failed to upload PDF for {pmid}")
            return False
        
        # Extract datapoints
        csv_data = self.extract_datapoints(document, pmid)
        if not csv_data:
            logger.error(f"Failed to extract data for {pmid}")
            return False
        
        # Save to CSV file
        self.save_to_csv(csv_data, pmid)
        
        logger.info(f"Successfully processed article {pmid}")
        return True
    
    def process_articles(self):
        """Main processing function."""
        logger.info("Starting data extraction from candidate articles")
        
        # Get candidate articles with PDFs
        candidate_articles = self.get_candidate_articles_with_pdfs()
        
        if not candidate_articles:
            logger.error("No candidate articles found with PDFs")
            return
        
        logger.info(f"Processing {len(candidate_articles)} candidate articles")
        
        # Initialize CSV file with headers if it doesn't exist
        if not os.path.exists('_extracted_datapoints.csv'):
            with open('_extracted_datapoints.csv', 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.csv_headers)
        
        # Process each candidate article
        processed_count = 0
        failed_count = 0
        
        for article in candidate_articles:
            pmid = article.get('pmid', 'unknown')
            try:
                success = self.process_single_article(article)
                if success:
                    processed_count += 1
                    logger.info(f"✓ Successfully processed article {pmid} ({processed_count}/{len(candidate_articles)})")
                else:
                    failed_count += 1
                    logger.warning(f"✗ Failed to process article {pmid} ({failed_count} failures so far)")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"✗ Exception processing article {pmid}: {str(e)}")
        
        # Final summary
        logger.info(f"Data extraction complete:")
        logger.info(f"  - Successfully processed: {processed_count} articles")
        logger.info(f"  - Failed: {failed_count} articles")
        logger.info(f"  - Results saved to: _extracted_datapoints.csv")
        
        # Display summary of extracted analysis
        logger.info(f"Extraction based on:")
        logger.info(f"  - Clinical Test: {self.analysis_info.get('selected_clinical_test', 'Unknown')}")
        logger.info(f"  - Recommended Cohorts: {len(self.analysis_info.get('recommended_cohorts', []))}")

# CLI Usage:
# python gemini_extract_datapoints.py
def main():
    """Main entry point."""
    import argparse
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Extract datapoints from candidate articles using Gemini API')
    
    args = parser.parse_args()
    
    # Set up environment
    if not os.getenv('GOOGLE_API_KEY'):
        logger.error("GOOGLE_API_KEY environment variable not set")
        return
    
    # Initialize extractor
    extractor = DataPointExtractor()
    
    # Process articles
    extractor.process_articles()

if __name__ == "__main__":
    main()