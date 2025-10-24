#!/usr/bin/env python3
"""
Gemini-based article processing script for medical research analysis.
Uses Google's Gemini API with context caching for efficient processing of PDF articles.

This script:
1. Loads articles from _pubmed_downloaded_articles.json
2. Caches PDF content with system prompt using Gemini context caching
3. Performs various classifications and extractions using cached context
4. Saves results to _classified_articles.json with status tracking
"""

import json
import os
import io
import httpx
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from dotenv import load_dotenv

from google import genai
from google.genai import types
import PyPDF2
from system_prompt_classifier import SYSTEM_PROMPT_CLASSIFIER
from prompt_classifier_article_type import PROMPT_CLASSIFIER_ARTICLE_TYPE
from prompt_classifier_candidate_meta_analysis import PROMPT_CLASSIFIER_CANDIDATE_META_ANALYSIS
from prompt_classifier_cochrane_bias import PROMPT_CLASSIFIER_COCHRANE_BIAS
from prompt_classifier_data_type import PROMPT_CLASSIFIER_DATA_TYPE
from prompt_classifier_species import PROMPT_CLASSIFIER_SPECIES
from prompt_classifier_study_type import PROMPT_CLASSIFIER_STUDY_TYPE
from prompt_extractor_clinical_test import PROMPT_EXTRACTOR_CLINICAL_TEST
from prompt_extractor_cohort import PROMPT_EXTRACTOR_COHORT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiArticleProcessor:
    def __init__(self, max_articles: int = 2):
        """
        Initialize the Gemini Article Processor.
        
        Args:
            max_articles: Maximum number of articles to process (default 2 for testing)
        """
        self.client = genai.Client()
        self.model_name = "gemini-flash-latest"
        self.max_articles = max_articles
        self.cache_objects = {}  # Store cache objects for each article
        
        # Load system prompt
        self.system_instruction = SYSTEM_PROMPT_CLASSIFIER
        
        # Load existing classification prompts
        self.classification_prompts = self._load_classification_prompts()
        
    def _load_classification_prompts(self) -> Dict[str, str]:
        """Load all classification prompts from imported constants."""
        prompts = {
            'article_type': PROMPT_CLASSIFIER_ARTICLE_TYPE,
            'candidate_meta_analysis': PROMPT_CLASSIFIER_CANDIDATE_META_ANALYSIS,
            'cochrane_bias': PROMPT_CLASSIFIER_COCHRANE_BIAS,
            'data_type': PROMPT_CLASSIFIER_DATA_TYPE,
            'species': PROMPT_CLASSIFIER_SPECIES,
            'study_type': PROMPT_CLASSIFIER_STUDY_TYPE,
            'clinical_test': PROMPT_EXTRACTOR_CLINICAL_TEST,
            'cohort': PROMPT_EXTRACTOR_COHORT
        }
        
        return prompts
    
    def load_articles(self) -> Dict[str, Any]:
        """Load articles from _classified_articles.json if it exists, otherwise from _pubmed_downloaded_articles.json."""
        # First try to load from _classified_articles.json (resume existing work)
        if os.path.exists('_classified_articles.json'):
            try:
                with open('_classified_articles.json', 'r') as f:
                    logger.info("Loading existing classified articles from _classified_articles.json")
                    return json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load _classified_articles.json: {e}, falling back to source file")
        
        # Fall back to original source file
        try:
            with open('_pubmed_downloaded_articles.json', 'r') as f:
                logger.info("Loading articles from _pubmed_downloaded_articles.json")
                return json.load(f)
        except FileNotFoundError:
            logger.error("_pubmed_downloaded_articles.json not found")
            return {"articles": []}
    
    def save_classified_articles(self, articles_data: Dict[str, Any]):
        """Save classified articles to _classified_articles.json."""
        # Add processing metadata
        articles_data['processing_metadata'] = {
            'processed_timestamp': datetime.now().isoformat(),
            'processor_version': '1.0',
            'model_used': self.model_name,
            'max_articles_processed': self.max_articles
        }
        
        with open('_classified_articles.json', 'w') as f:
            json.dump(articles_data, f, indent=2, ensure_ascii=False)
        logger.info("Saved classified articles to _classified_articles.json")
    
    def create_cache_for_article(self, pdf_path: str, pmid: str) -> Optional[Any]:
        """
        Create a cached content object for a PDF article.
        
        Args:
            pdf_path: Path to the PDF file
            pmid: PubMed ID for identification
            
        Returns:
            Cache object or None if failed
        """
        try:
            # Check if PDF file exists
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF file not found: {pdf_path}")
                return None
            
            # Upload PDF file           
            document = self.client.files.upload(
                file=pdf_path,
                config=dict(mime_type='application/pdf')
            )
            
            # Create cached content
            cache = self.client.caches.create(
                model=self.model_name,
                config=types.CreateCachedContentConfig(
                    system_instruction=self.system_instruction,
                    contents=[document],
                )
            )
            
            logger.info(f"Created cache for article {pmid}: {cache.name}")
            return cache
            
        except Exception as e:
            logger.error(f"Failed to create cache for {pmid}: {str(e)}")
            return None
    
    def classify_article(self, cache: Any, classification_type: str, prompt: str) -> Optional[str]:
        """
        Perform a specific classification using cached content.
        
        Args:
            cache: Cached content object
            classification_type: Type of classification
            prompt: Classification prompt
            
        Returns:
            Classification result or None if failed
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    cached_content=cache.name,
                    response_mime_type="application/json"
                )
            )
            
            logger.info(f"Completed {classification_type} classification")
            return response.text
            
        except Exception as e:
            logger.error(f"Failed {classification_type} classification: {str(e)}")
            return None
    
    def process_single_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single article through all classification steps.
        
        Args:
            article: Article data dictionary
            
        Returns:
            Updated article with classification results
        """
        pmid = article.get('pmid', 'unknown')
        pdf_path = article.get('pdf_path')
        
        # Check if already processed
        if article.get('classifier_status') == 'done':
            logger.info(f"Article {pmid} already processed, skipping")
            return article
        
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning(f"No valid PDF for article {pmid}")
            article['classifier_status'] = 'no_pdf'
            return article
        
        if article.get('classifier_status') == 'cache_failed':
            logger.warning(f"Reported cache issue {pmid}")
            return article
        
        
        
        logger.info(f"Processing article {pmid}")
        
        # Create cache for this article
        cache = self.create_cache_for_article(pdf_path, pmid)
        if not cache:
            article['classifier_status'] = 'cache_failed'
            return article
        
        # Initialize classifier results
        article['classifier_results'] = {}
        
        # Perform all classifications
        classifications = [
            'candidate_meta_analysis',
            'article_type',
            'cochrane_bias',
            'data_type',
            'species',
            'study_type',
            'clinical_test',
            'cohort'
        ]
        
        for class_type in classifications:
            # Use specific prompt if available, otherwise use description
            prompt = self.classification_prompts.get(class_type)
            
            result = self.classify_article(cache, class_type, prompt)
            try:
                result_json = json.loads(result)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse {class_type} result for {pmid}: {e}")
                # Continue with other classifiers if JSON parsing fails

            article['classifier_results'][class_type] = {
                'result': result_json,
                'timestamp': datetime.now().isoformat(),
                'status': 'completed' if result else 'failed'
            }
            
            # If candidate_meta_analysis classification returns "NOT A CANDIDATE", skip remaining classifiers
            if class_type == 'candidate_meta_analysis' and result:
                candidacy = result_json.get('candidacy_classification', '').upper()
                if candidacy == 'NOT_A_CANDIDATE':
                    logger.info(f"Article {pmid} not a candidate for meta-analysis, skipping remaining classifiers")
                    break
                    
        # Mark as processed
        article['classifier_status'] = 'done'
        article['processing_timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Completed processing article {pmid}")
        return article
    
    def check_pdf_pages(self, pdf_path: str) -> Optional[int]:
        """
        Check the number of pages in a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Number of pages or None if failed to read
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                logger.info(f"PDF {pdf_path} has {num_pages} pages")
                return num_pages
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {str(e)}")
            return None
    
    def shrink_pdf(self, pdf_path: str, max_pages: int = 30) -> Optional[str]:
        """
        Create a shrunk version of PDF with maximum specified pages.
        
        Args:
            pdf_path: Path to the original PDF file
            max_pages: Maximum number of pages to include (default: 30)
            
        Returns:
            Path to the shrunk PDF or None if failed
        """
        try:
            # Generate output filename
            pdf_pathlib = Path(pdf_path)
            output_filename = f"{pdf_pathlib.stem}_{max_pages}_pages_version.pdf"
            output_path = pdf_pathlib.parent / output_filename
            
            # Read original PDF
            with open(pdf_path, 'rb') as input_file:
                reader = PyPDF2.PdfReader(input_file)
                writer = PyPDF2.PdfWriter()
                
                # Add only the first max_pages pages
                pages_to_add = min(len(reader.pages), max_pages)
                for page_num in range(pages_to_add):
                    writer.add_page(reader.pages[page_num])
                
                # Write shrunk PDF
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            logger.info(f"Created shrunk PDF: {output_path} ({pages_to_add} pages)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to shrink PDF {pdf_path}: {str(e)}")
            return None
    
    def process_pdf_for_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check PDF page count and shrink if necessary for an article.
        
        Args:
            article: Article data dictionary containing pdf_path
            
        Returns:
            Updated article with pdf_pages, and potentially pdf_path_original and updated pdf_path
        """
        # Check if PDF has already been processed
        if article.get('pdf_pages') is not None and article.get('pdf_path_original') is not None:
            logger.info(f"PDF already processed for article, skipping PDF processing")
            return article
        
        pdf_path = article['pdf_path']
        page_count = self.check_pdf_pages(pdf_path)
        
        if page_count is not None:
            article['pdf_pages'] = page_count
            
            if page_count > 30:
                logger.info(f"PDF has {page_count} pages, creating 30-page version")
                shrunk_pdf_path = self.shrink_pdf(pdf_path, 30)
                
                if shrunk_pdf_path:
                    article['pdf_path_original'] = pdf_path
                    article['pdf_path'] = shrunk_pdf_path
                    logger.info(f"Updated article to use shrunk PDF: {shrunk_pdf_path}")
                else:
                    logger.warning(f"Failed to shrink PDF, using original: {pdf_path}")
        
        return article
    
    def process_articles(self):
        """Main processing function."""
        logger.info("Starting article processing")
        
        # Load articles
        articles_data = self.load_articles()
        articles = articles_data.get('articles', [])
        
        if not articles:
            logger.error("No articles found to process")
            return
        
        # Filter articles with PDF files
        articles_with_pdf = [
            article for article in articles 
            if article.get('pdf_path') and os.path.exists(article['pdf_path'])
        ]
        
        logger.info(f"Found {len(articles_with_pdf)} articles with PDF files")
        
        # Limit to max_articles for processing
        articles_to_process = articles_with_pdf[:self.max_articles]
        logger.info(f"Processing {len(articles_to_process)} articles (limited to {self.max_articles})")
        
        # Process each article
        processed_count = 0
        for i, article in enumerate(articles):
            if article.get('pdf_path') and os.path.exists(article['pdf_path']) and processed_count < self.max_articles:
                
                # Check PDF page count and shrink if necessary
                articles[i] = self.process_pdf_for_article(article)
                article = articles[i]
                articles[i] = self.process_single_article(article)
                processed_count += 1
                
                # Save progress after each article is processed
                articles_data['articles'] = articles
                self.save_classified_articles(articles_data)
                logger.info(f"Saved progress after processing article {processed_count}/{self.max_articles}")
                
            elif not article.get('classifier_status'):
                # Mark articles without PDF as skipped
                articles[i]['classifier_status'] = 'no_pdf'
        
        # Final save (in case there were any no_pdf status updates)
        articles_data['articles'] = articles
        self.save_classified_articles(articles_data)
        
        logger.info(f"Processing complete. Processed {processed_count} articles.")

# CLI Usage:
# python gemini_classify_articles.py --max-articles 5
# python gemini_classify_articles.py --force --max-articles 10
def main():
    """Main entry point."""
    import argparse
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Process articles with Gemini API')
    parser.add_argument('--max-articles', type=int, default=2, 
                       help='Maximum number of articles to process (default: 2)')
    parser.add_argument('--force', action='store_true',
                       help='Reprocess articles even if already done')
    
    args = parser.parse_args()
    
    # Set up environment
    if not os.getenv('GOOGLE_API_KEY'):
        logger.error("GOOGLE_API_KEY environment variable not set")
        return
    
    # Initialize processor
    processor = GeminiArticleProcessor(max_articles=args.max_articles)
    
    # Process articles
    processor.process_articles()

if __name__ == "__main__":
    main()