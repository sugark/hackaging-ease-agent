#!/usr/bin/env python3
"""
PubMed Search Query Generator using Google Gemini API Flash Model
Generates comprehensive search queries for PubMed API service based on input topics.
"""

import os
import json
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from google.api_core import retry
from dotenv import load_dotenv
from system_prompt_generate_search_query import SYSTEM_PROMPT_GENERATE_SEARCH_QUERY

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure retry for API rate limiting and temporary errors
def is_retriable(e):
    """
    Check if an API error is retriable (rate limit or server error).
    
    Args:
        e: Exception to check
        
    Returns:
        bool: True if the error should be retried
    """
    # Check for google.generativeai API errors
    if hasattr(e, 'code') and e.code in {429, 503}:
        logger.warning(f"Retriable API error encountered: {e.code}. Retrying...")
        return True
    return False

# Model configuration
MODEL = "gemini-flash-latest"

def generate_pubmed_queries(input_topic: str, api_key: str = None) -> Dict[str, Any]:
    """
    Generate comprehensive PubMed search queries for a given research topic using Gemini AI.
    
    Args:
        input_topic (str): The research topic to generate queries for
        api_key (str, optional): Google AI API key (uses GOOGLE_API_KEY env var if not provided)
        
    Returns:
        Dict[str, Any]: Dictionary containing generated queries and metadata
    """
    
    try:
        # Get API key from parameter or environment
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return {
                    "status": "error",
                    "message": "Google AI API key is required. Set GOOGLE_API_KEY environment variable or provide api_key parameter.",
                    "input_topic": input_topic
                }
        
        # Configure Gemini AI
        client = genai.Client(api_key=api_key)
        
        
        # System prompt for generating PubMed search queries with emphasis on synonyms
        system_prompt = SYSTEM_PROMPT_GENERATE_SEARCH_QUERY

        # Generate queries using Gemini with retry
        retry_decorator = retry.Retry(
            predicate=is_retriable,
            initial=1.0,      # Initial delay of 1 second
            maximum=60.0,     # Maximum delay of 60 seconds
            multiplier=2.0,   # Exponential backoff multiplier
            deadline=300.0    # Total deadline of 5 minutes
        )
        
        @retry_decorator
        def generate_with_retry():
            return client.models.generate_content(
                model=MODEL,
                contents=system_prompt)

        response = generate_with_retry()
        
        # Parse the JSON response
        response_text = response.text.strip()
        
        # Clean up the response if it has markdown formatting
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
        
        queries_result = json.loads(response_text)
        
        return {
            "status": "success",
            "input_topic": input_topic,
            "generated_queries": queries_result,
            "total_queries": len(queries_result.get("queries", [])),
            "usage_instructions": {
                "api_usage": "Use these queries with PubMed E-utilities API",
                "rate_limiting": "Respect NCBI rate limits (3 requests/second max)",
                "email_required": "Set NCBI_EMAIL environment variable"
            },
            "generation_method": "gemini_ai"
        }
        
    except Exception as e:
        logger.error(f"Error generating PubMed queries: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to generate queries: {str(e)}",
            "input_topic": input_topic
        }





# Initialize Gemini AI configuration
def configure_gemini(api_key: str = None):
    """Configure Gemini AI with API key."""
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google AI API key is required. Set GOOGLE_API_KEY environment variable.")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL)


"""
CLI USAGE:
----------

Prerequisites:
1. Set up Google AI API key:
   - Get API key from: https://makersuite.google.com/app/apikey
   - Option A: Create .env file with: GOOGLE_API_KEY=your_api_key_here
   - Option B: Export environment variable: export GOOGLE_API_KEY='your_api_key_here'

2. Create input file:
   - Create '_input_topic.md' in the same directory
   - Add your research topic as plain text (e.g., "resveratrol and diabetes")

3. Install dependencies:
   pip install google-generativeai python-dotenv

Basic Usage:
   python pubmed_generate_search.py

Output:
   - Console output with generated queries and analysis
   - JSON file: '_pubmed_generate_search_out.json' with complete results

Example workflow:
   echo "machine learning in medical diagnosis" > _input_topic.md
   python pubmed_generate_search.py
   
The script will generate 6-8 comprehensive PubMed search queries optimized for
systematic reviews and meta-analyses, excluding review papers to focus on 
primary research studies.
"""

def main():
    """Main function to demonstrate the PubMed query generator."""
    
    # Read input topic from file
    try:
        with open("_input_topic.md", "r", encoding="utf-8") as f:
            input_topic = f.read().strip()
        
        if not input_topic:
            print("❌ Error: _input_topic.md file is empty")
            return
            
    except FileNotFoundError:
        print("❌ Error: _input_topic.md file not found")
        print("   Please create _input_topic.md with your research topic")
        return
    except Exception as e:
        print(f"❌ Error reading _input_topic.md: {str(e)}")
        return
    
    print(f"🔍 Generating PubMed search queries for topic: '{input_topic}'")
    print("🔄 API retry functionality enabled for rate limiting and temporary errors")
    
    # Check if .env file exists
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        print("✅ .env file found and loaded")
    else:
        print("ℹ️  No .env file found (using system environment variables)")
    print()
    
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: No GOOGLE_API_KEY found in environment variables.")
        print("   Please set GOOGLE_API_KEY to use Gemini AI for query generation.")
        print("   ")
        print("   Options:")
        print("   1. Create a .env file with: GOOGLE_API_KEY=your_api_key_here")
        print("   2. Export environment variable: export GOOGLE_API_KEY='your_api_key_here'")
        print("   3. Get API key from: https://makersuite.google.com/app/apikey")
        print("   ")
        print("   See .env.example file for template.\n")
        return
    
    try:
        # Generate queries
        result = generate_pubmed_queries(input_topic)
        
        if result["status"] == "success":
            print("✅ Query generation successful!")
            print(f"📊 Total queries generated: {result['total_queries']}")
            print(f"🤖 Generation method: {result.get('generation_method', 'unknown')}\n")
            
            # Print the queries in a readable format
            queries_data = result["generated_queries"]
            
            print("📋 Generated PubMed Search Queries:")
            print("=" * 60)
            
            for i, query in enumerate(queries_data.get("queries", []), 1):
                print(f"\n{i}. {query['query_type']}")
                print(f"   Query: {query['query_string']}")
                print(f"   Rationale: {query['rationale']}")
            
            # Print synonyms if available
            if "synonyms_identified" in queries_data:
                synonyms = queries_data["synonyms_identified"]
                if synonyms:
                    print(f"\n🔤 Synonyms Identified:")
                    print("-" * 30)
                    for concept, concept_synonyms in synonyms.items():
                        if concept_synonyms:
                            print(f"   {concept}: {', '.join(concept_synonyms[:5])}")  # Show first 5
                            if len(concept_synonyms) > 5:
                                print(f"      ... and {len(concept_synonyms) - 5} more")
            
            # Print topic analysis
            if "topic_analysis" in queries_data:
                analysis = queries_data["topic_analysis"]
                print(f"\n📊 Topic Analysis:")
                print("-" * 20)
                print(f"   Main concepts: {', '.join(analysis.get('main_concepts', []))}")
                print(f"   Suggested MeSH terms: {', '.join(analysis.get('suggested_mesh_terms', []))}")
                print(f"   Relevant study types: {', '.join(analysis.get('study_types', []))}")
            
            # Print usage instructions
            print(f"\n💡 Usage Instructions:")
            print("-" * 22)
            instructions = result["usage_instructions"]
            for key, value in instructions.items():
                print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Save to JSON file
            output_file = "_pubmed_generate_search_out.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {output_file}")
            
            # Print example usage
            print(f"\n🚀 Example Usage with PubMed API:")
            print("-" * 35)
            if queries_data.get("queries"):
                example_query = queries_data["queries"][0]["query_string"]
                print(f"   Query: {example_query}")
                print(f"   URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={example_query.replace(' ', '+')}")
            
        else:
            print(f"❌ Error: {result['message']}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Main function error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()