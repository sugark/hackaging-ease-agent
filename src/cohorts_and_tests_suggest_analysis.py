#!/usr/bin/env python3
"""
Script to analyze cohorts and clinical tests data for meta-analysis suggestions.

This script:
1. Loads system prompt from system_prompt_suggest_analysis.py
2. Reads CSV data from _cohorts_and_tests.csv
3. Uses Gemini to analyze the data and suggest clinical tests and cohort groups for meta-analysis
4. Saves recommendations to _suggested_analysis.json in structured JSON format

CLI Best Practices:
Run with: python cohorts_and_tests_suggest_analysis.py
Ensure system_prompt_suggest_analysis.py and _cohorts_and_tests.csv exist in the same directory
Set GOOGLE_API_KEY in .env file for Gemini API calls
Use conda activate hackathlon before running
"""

import os
import json
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from system_prompt_suggest_analysis import SYSTEM_PROMPT_SUGGEST_ANALYSIS

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CohortsTestsAnalyzer:
    """Class for analyzing cohorts and clinical tests data using Gemini AI."""
    
    def __init__(self, system_prompt_file: str = "system_prompt_suggest_analysis.py", 
                 csv_data_file: str = "_cohorts_and_tests.csv"):
        """
        Initialize CohortsTestsAnalyzer with API key and file paths.
        
        Args:
            system_prompt_file: Path to the system prompt Python file (kept for compatibility)
            csv_data_file: Path to the CSV data file
        """

        # Load environment variables
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
            return
        
        self.api_key = api_key
        self.csv_data_file = csv_data_file
        self.MODEL="gemini-1.5-pro"
        
        # Initialize Gemini client
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.genai = genai
            logger.info("Gemini API configured successfully")
        except ImportError:
            logger.error("google.generativeai not installed. Install with: pip install google-generativeai")
            self.genai = None
        
        # Use imported system prompt constant
        self.system_prompt = SYSTEM_PROMPT_SUGGEST_ANALYSIS
        logger.info("Using imported SYSTEM_PROMPT_SUGGEST_ANALYSIS constant")

    def read_csv_content(self) -> str:
        """
        Read the CSV content from _cohorts_and_tests.csv with error handling.
        
        Returns:
            CSV content string or empty string if file not found/invalid
        """
        try:
            with open(self.csv_data_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"Successfully loaded CSV data from {self.csv_data_file}")
                return content
        except FileNotFoundError:
            logger.error(f"Error: File {self.csv_data_file} not found")
            return ""
        except Exception as e:
            logger.error(f"Error reading CSV content: {e}")
            return ""

    def generate_gemini_content(self, system_prompt: str, csv_content: str) -> list:
        """
        Generate structured content array for Gemini API.
        
        Args:
            system_prompt: The system prompt for analysis instructions
            csv_content: The CSV data containing cohorts, clinical tests, and species
            
        Returns:
            List of content parts for Gemini API
        """
        content = [
            f"{system_prompt}\n\nIMPORTANT: You MUST respond with valid JSON only. No additional text, explanations, or formatting outside the JSON object.",
            f"Here is the CSV data containing cohorts, clinical tests, and species information extracted from classified scientific and medical papers:\n\n{csv_content}",
            "Please analyze this data and provide your recommendations in the specified JSON format."
        ]
        
        return content

    def query_gemini(self, csv_content: str) -> dict:
        """
        Query Gemini API with analysis content and return parsed JSON response.
        
        Args:
            csv_content: The CSV data containing cohorts, clinical tests, and species
            
        Returns:
            Parsed JSON dict or error dict if API call fails
        """
        if not self.api_key:
            return {"error": "API key not provided during initialization."}
            
        if not self.genai:
            return {"error": "Gemini client not initialized. Check API key and dependencies."}
            
        try:
            # Create prompt with system instruction and data
            prompt = f"{self.system_prompt}\n\n{csv_content}\n\nPlease respond with valid JSON only."
            
            # Initialize Gemini model and generate content
            model = self.genai.GenerativeModel(self.MODEL)
            response = model.generate_content(
                prompt,
                generation_config=self.genai.types.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON response
            try:
                json_response = json.loads(response.text.strip())
                return json_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return {"error": f"Invalid JSON response from Gemini: {response.text}"}
                
        except ImportError:
            return {"error": "google.generativeai module not installed. Please install with: pip install google-generativeai"}
        except Exception as e:
            logger.error(f"Error querying Gemini: {e}")
            return {"error": f"Unable to query Gemini API. {e}"}

    def save_to_json(self, data: dict, filename: str = "_suggested_analysis.json") -> None:
        """
        Save analysis results to JSON file.
        
        Args:
            data: Dictionary containing analysis results
            filename: Output JSON filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON file: {e}")

    def run_analysis(self) -> None:
        """
        Main workflow to analyze cohorts and clinical tests data and generate recommendations.
        
        Performs complete pipeline: load CSV data, query Gemini API, save results to JSON, 
        and display results or diagnostic information.
        """
        logger.info("Starting cohorts and clinical tests analysis...")
        
        # Check if system prompt is available
        if not self.system_prompt:
            logger.error("No system prompt available. Exiting.")
            return
        
        # Read the CSV data
        csv_content = self.read_csv_content()
        if not csv_content:
            logger.error("No CSV data loaded. Exiting.")
            return
        
        # Query Gemini
        logger.info("Querying Gemini for meta-analysis recommendations...")
        gemini_response = self.query_gemini(csv_content)
        
        # Save to JSON file
        self.save_to_json(gemini_response)
        
        # Display results
        print("\n" + "="*80)
        print("COHORTS AND CLINICAL TESTS ANALYSIS RESULTS")
        print("="*80)
        print(json.dumps(gemini_response, indent=2, ensure_ascii=False))
        print("\n" + "="*80)


def main():
    """Main function to run the cohorts and tests analyzer."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    system_prompt_file = os.path.join(script_dir, "system_prompt_suggest_analysis.py")
    csv_data_file = os.path.join(script_dir, "_cohorts_and_tests.csv")
    
    analyzer = CohortsTestsAnalyzer(system_prompt_file, csv_data_file)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()