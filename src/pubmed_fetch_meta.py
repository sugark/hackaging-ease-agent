#!/usr/bin/env python3
"""
Script to run PubMed queries from the generated JSON file and merge results
"""

import json
import os
from typing import List
from dotenv import load_dotenv

# Import from tools subdirectory
from tools.pubmed.pubmed_search import PubMedSearcher, PubMedArticle

def load_queries(json_file: str) -> List[dict]:
    """Load queries from the JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        queries = data.get('generated_queries', {}).get('queries', [])
        print(f"Loaded {len(queries)} queries from {json_file}")
        return queries
    except Exception as e:
        print(f"Error loading queries: {e}")
        return []

def run_all_queries(searcher: PubMedSearcher, queries: List[dict], max_results_per_query: int = 50) -> List[List[PubMedArticle]]:
    """Run all queries and return list of result lists"""
    all_results = []
    
    for i, query_info in enumerate(queries, 1):
        query_string = query_info.get('query_string', '')
        query_type = query_info.get('query_type', 'Unknown')
        
        print(f"\n--- Query {i}/{len(queries)}: {query_type} ---")
        print(f"Query: {query_string}")
        
        try:
            results = searcher.search(
                query=query_string,
                max_results=max_results_per_query,
                sort="relevance"
            )
            
            print(f"Found {len(results)} articles")
            all_results.append(results)
            
        except Exception as e:
            print(f"Error running query {i}: {e}")
            all_results.append([])  # Add empty list for failed query
    
    return all_results

"""
CLI Usage:
    python pubmed_fetch_meta.py

Prerequisites:
    1. Set NCBI_EMAIL environment variable:
       export NCBI_EMAIL="your.email@example.com"
       OR create .env file with: NCBI_EMAIL=your.email@example.com
    
    2. Ensure input file exists:
       _pubmed_generate_search_out.json
    
    3. Run from the ease_agent directory

Optional Configuration:
    MAX_RESULTS_PER_QUERY=50 (default: 30) - Maximum results per query

Output:
    - Console progress and statistics
    - _pubmed_fetched_meta_results.json (exported results)
"""
def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration
    json_file = '_pubmed_generate_search_out.json'
    email = os.getenv('NCBI_EMAIL', 'user@example.com')
    max_results_per_query = int(os.getenv('MAX_RESULTS_PER_QUERY', '30'))  # Configurable via env var
    
    print("=== PubMed Query Runner ===")
    print(f"Email: {email}")
    print(f"Max results per query: {max_results_per_query}")
    
    # Load queries
    queries = load_queries(json_file)
    if not queries:
        print("No queries found. Exiting.")
        return
    
    # Initialize searcher
    try:
        searcher = PubMedSearcher(email=email, rate_limit=0.5)  # Slightly slower to be safe
        print(f"PubMedSearcher initialized successfully")
    except Exception as e:
        print(f"Error initializing PubMedSearcher: {e}")
        return
    
    # Run all queries
    print(f"\n=== Running {len(queries)} queries ===")
    all_results = run_all_queries(searcher, queries, max_results_per_query)
    
    # Merge results
    print(f"\n=== Merging Results ===")
    merged_results = searcher.search_merge(all_results)
    
    # Print summary
    total_articles = sum(len(results) for results in all_results)
    print(f"\nSUMMARY:")
    print(f"- Total articles from all queries: {total_articles}")
    print(f"- Unique articles after merging: {len(merged_results)}")
    print(f"- Duplicates removed: {total_articles - len(merged_results)}")
    
    # Get statistics
    stats = searcher.get_search_statistics(merged_results)
    print(f"\nSTATISTICS:")
    for key, value in stats.items():
        if key == 'articles_by_year':
            print(f"- {key}: {dict(sorted(value.items(), reverse=True)[:5])}")  # Top 5 years
        elif key == 'top_journals':
            print(f"- {key}: {dict(list(value.items())[:3])}")  # Top 3 journals
        else:
            print(f"- {key}: {value}")
    
    # Export results
    output_file = '_pubmed_fetched_meta_results.json'
    searcher.export_to_json(merged_results, output_file)
    print(f"\nResults exported to: {output_file}")
    
    # Show sample articles
    print(f"\n=== Sample Articles ===")
    for i, article in enumerate(merged_results[:3], 1):
        print(f"\nArticle {i}:")
        print(f"  PMID: {article.pmid}")
        print(f"  Title: {article.title[:80]}...")
        print(f"  Authors: {', '.join(article.authors[:2])}{'...' if len(article.authors) > 2 else ''}")
        print(f"  Journal: {article.journal}")
        print(f"  Date: {article.publication_date}")
        print(f"  DOI: {article.doi or 'N/A'}")

if __name__ == "__main__":
    main()