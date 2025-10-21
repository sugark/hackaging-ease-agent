import json
import os
import time
from typing import List, Dict, Any
from google import genai
from google.genai import types
from google.api_core import retry
from dataclasses import dataclass
import logging
from dotenv import load_dotenv
from system_prompt_filter_abstracts import SYSTEM_PROMPT_FILTER_ABSTRACTS

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model configuration
MODEL = "gemini-flash-latest"

# Configure retry for API rate limiting and temporary errors
def is_retriable(e):
    """
    Check if an API error is retriable (rate limit or server error).
    
    Args:
        e: Exception to check
        
    Returns:
        bool: True if the error should be retried
    """
    # Check for google.genai API errors
    if hasattr(e, 'code') and e.code in {429, 503}:
        logger.warning(f"Retriable API error encountered: {e.code}. Retrying...")
        return True
    return False

def get_gemini_api_key():
    """Get Gemini API key from environment variables"""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logging.error("GOOGLE_API_KEY not found in environment variables")
        raise ValueError("GOOGLE_API_KEY must be set in environment variables")
    return api_key

def get_batch_config():
    """Get batch processing configuration"""
    return {
        'batch_size': int(os.getenv('BATCH_SIZE', '100')),
        'delay_between_batches': float(os.getenv('BATCH_DELAY', '2.0')),
        'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        'timeout': int(os.getenv('API_TIMEOUT', '30'))
    }

@dataclass
class ArticleClassification:
    pmid: str
    is_good_candidate: bool
    reasons: List[str]
    confidence_score: float = 0.0

class GeminiArticleFilter:
    def __init__(self, api_key: str):
        """Initialize Gemini AI client"""
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.system_prompt = SYSTEM_PROMPT_FILTER_ABSTRACTS
           
    def classify_articles_batch(self, articles_batch: List[Dict[str, Any]]) -> List[ArticleClassification]:
        """Classify a batch of articles using Gemini"""
        try:
            # Prepare batch prompt
            batch_content = self._prepare_batch_prompt(articles_batch)
            
            # Configure retry decorator
            retry_decorator = retry.Retry(
                predicate=is_retriable,
                initial=1.0,      # Initial delay of 1 second
                maximum=60.0,     # Maximum delay of 60 seconds
                multiplier=2.0,   # Exponential backoff multiplier
                deadline=300.0    # Total deadline of 5 minutes
            )
            
            @retry_decorator
            def generate_with_retry():
                return self.client.models.generate_content(
                    model=MODEL,
                    contents=f"{self.system_prompt}\n\n{batch_content}")
            
            # Make API call to Gemini with retry
            response = generate_with_retry()
            
            # Parse response
            classifications = self._parse_response(response.text, articles_batch)
            return classifications
            
        except Exception as e:
            logger.error(f"Error in batch classification: {str(e)}")
            # Return default classifications for failed batch
            return [
                ArticleClassification(
                    pmid=article.get('pmid', 'unknown'),
                    is_good_candidate=False,
                    reasons=[f"Classification failed: {str(e)}"],
                    confidence_score=0.0
                )
                for article in articles_batch
            ]
    
    def _prepare_batch_prompt(self, articles_batch: List[Dict[str, Any]]) -> str:
        """Prepare the prompt for a batch of articles"""
        prompt = "Please classify the following articles for meta-analysis inclusion:\n\n"
        
        for i, article in enumerate(articles_batch, 1):
            pmid = article.get('pmid', 'unknown')
            title = article.get('title', 'No title available')
            abstract = article.get('abstract', 'No abstract available')
            
            prompt += f"ARTICLE {i}:\n"
            prompt += f"PMID: {pmid}\n"
            prompt += f"TITLE: {title}\n"
            prompt += f"ABSTRACT: {abstract}\n\n"
        
        prompt += "Please provide your classification for each article as a JSON array."
        return prompt
    
    def _parse_response(self, response_text: str, articles_batch: List[Dict[str, Any]]) -> List[ArticleClassification]:
        """Parse Gemini response into ArticleClassification objects"""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                # Try to find individual JSON objects
                classifications = []
                for article in articles_batch:
                    pmid = article.get('pmid', 'unknown')
                    # Look for this PMID in the response
                    if pmid in response_text:
                        # Extract relevant portion and try to parse
                        classifications.append(
                            ArticleClassification(
                                pmid=pmid,
                                is_good_candidate=True,  # Default to true for manual review
                                reasons=["Parsing failed - manual review needed"],
                                confidence_score=0.5
                            )
                        )
                    else:
                        classifications.append(
                            ArticleClassification(
                                pmid=pmid,
                                is_good_candidate=False,
                                reasons=["Response parsing failed"],
                                confidence_score=0.0
                            )
                        )
                return classifications
            
            json_str = response_text[start_idx:end_idx]
            parsed_data = json.loads(json_str)
            
            classifications = []
            for item in parsed_data:
                classifications.append(
                    ArticleClassification(
                        pmid=item.get('pmid', 'unknown'),
                        is_good_candidate=item.get('is_good_candidate', False),
                        reasons=item.get('reasons', []),
                        confidence_score=item.get('confidence_score', 0.0)
                    )
                )
            
            return classifications
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            # Return default classifications
            return [
                ArticleClassification(
                    pmid=article.get('pmid', 'unknown'),
                    is_good_candidate=False,
                    reasons=["JSON parsing failed"],
                    confidence_score=0.0
                )
                for article in articles_batch
            ]

def load_merged_articles(file_path: str) -> List[Dict[str, Any]]:
    """Load articles from _pubmed_fetched_meta_results.json"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('articles', [])
    except Exception as e:
        logger.error(f"Error loading articles: {str(e)}")
        return []

def save_filtered_results(classifications: List[ArticleClassification], output_path: str):
    """Save classification results to JSON file"""
    try:
        # Convert classifications to dictionary format
        results = {
            "metadata": {
                "total_articles_classified": len(classifications),
                "good_candidates": len([c for c in classifications if c.is_good_candidate]),
                "bad_candidates": len([c for c in classifications if not c.is_good_candidate]),
                "classification_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "classifier": "Gemini AI"
            },
            "classifications": [
                {
                    "pmid": c.pmid,
                    "is_good_candidate": c.is_good_candidate,
                    "reasons": c.reasons,
                    "confidence_score": c.confidence_score
                }
                for c in classifications
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

def main():
    """
    Main function to process articles with Gemini AI classification.
    
    CLI Usage:
        python pubmed_filter_abstracts.py
    
    Environment Variables Required:
        GOOGLE_API_KEY - Your Google Gemini API key
    
    Optional Environment Variables:
        BATCH_SIZE - Number of articles to process per batch (default: 100)
        BATCH_DELAY - Delay between batches in seconds (default: 2.0)
        INPUT_FILE - Path to _pubmed_fetched_meta_results.json (default: ./_pubmed_fetched_meta_results.json)
        OUTPUT_FILE - Path for output file (default: ./_pubmed_filtered_articles.json)
    
    Input File Format:
        JSON file with structure: {"articles": [{"pmid": "...", "abstract": "...", ...}]}
    
    Output File Format:
        JSON file with classification results and metadata
    
    Example:
        # Set environment variables
        export GOOGLE_API_KEY="your_api_key_here"
        export BATCH_SIZE=50
        
        # Run the script
        python filter_articles_with_gemini.py
    """
    # Configuration
    input_file = os.getenv('INPUT_FILE', "./_pubmed_fetched_meta_results.json")
    output_file = os.getenv('OUTPUT_FILE', "./_pubmed_filtered_articles.json")
    batch_size = int(os.getenv('BATCH_SIZE', '100'))
    delay_between_batches = float(os.getenv('BATCH_DELAY', '2.0'))
    
    # Get API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set")
        logger.error("Please set your Google AI API key: export GOOGLE_API_KEY='your_key_here'")
        return
    
    # Load articles
    logger.info("Loading articles...")
    articles = load_merged_articles(input_file)
    if not articles:
        logger.error("No articles loaded")
        return
    
    logger.info(f"Loaded {len(articles)} articles")
    
    # Initialize classifier
    classifier = GeminiArticleFilter(api_key)
    
    # Process articles in batches
    all_classifications = []
    total_batches = (len(articles) + batch_size - 1) // batch_size
    
    for i in range(0, len(articles), batch_size):
        batch_num = (i // batch_size) + 1
        batch = articles[i:i + batch_size]
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} articles)")
        
        try:
            classifications = classifier.classify_articles_batch(batch)
            all_classifications.extend(classifications)
            
            logger.info(f"Batch {batch_num} completed: {len([c for c in classifications if c.is_good_candidate])} good candidates")
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_num}: {str(e)}")
            # Add default classifications for failed batch
            for article in batch:
                all_classifications.append(
                    ArticleClassification(
                        pmid=article.get('pmid', 'unknown'),
                        is_good_candidate=False,
                        reasons=[f"Batch processing failed: {str(e)}"],
                        confidence_score=0.0
                    )
                )
        
        # Delay between batches to respect API limits
        if i + batch_size < len(articles):
            time.sleep(delay_between_batches)
    
    # Save results
    logger.info("Saving classification results...")
    save_filtered_results(all_classifications, output_file)
    
    # Summary
    good_candidates = len([c for c in all_classifications if c.is_good_candidate])
    total_classified = len(all_classifications)
    
    logger.info(f"Classification complete!")
    logger.info(f"Total articles: {total_classified}")
    logger.info(f"Good candidates: {good_candidates}")
    logger.info(f"Bad candidates: {total_classified - good_candidates}")
    logger.info(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
