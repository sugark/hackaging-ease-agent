"""
Example usage of the PubMed Search module.

This script demonstrates how to use the PubMedSearcher class for:
1. Searching PubMed with advanced queries
2. Merging multiple search results
3. Exporting results and getting statistics
"""

import os
from pubmed_search import PubMedSearcher

def main():
    # Set your email (required by NCBI)
    # You can set this as an environment variable or replace with your actual email
    email = os.getenv("NCBI_EMAIL", "your.email@example.com")
    
    if email == "your.email@example.com":
        print("⚠️  Please set your email address either by:")
        print("   1. Setting NCBI_EMAIL environment variable: export NCBI_EMAIL='your.email@example.com'")
        print("   2. Or modify the email variable in this script")
        return
    
    # Initialize the searcher
    searcher = PubMedSearcher(email=email)
    
    print("🔍 PubMed Search Example")
    print("=" * 50)
    
    # Example 1: Search for COVID-19 vaccine articles
    print("\n1. Searching for COVID-19 vaccine articles...")
    covid_results = searcher.search(
        query="covid-19 AND vaccine",
        max_results=20
    )
    print(f"   Found {len(covid_results)} articles")
    
    # Example 2: Search for machine learning in radiology
    print("\n2. Searching for machine learning in radiology...")
    ml_results = searcher.search(
        query="machine learning[Title/Abstract] AND radiology",
        max_results=15
    )
    print(f"   Found {len(ml_results)} articles")
    
    # Example 3: Search for cancer immunotherapy
    print("\n3. Searching for cancer immunotherapy...")
    cancer_results = searcher.search(
        query="cancer AND immunotherapy AND clinical trial",
        max_results=10
    )
    print(f"   Found {len(cancer_results)} articles")
    
    # Example 4: Merge all search results
    print("\n4. Merging all search results...")
    all_search_results = [covid_results, ml_results, cancer_results]
    merged_results = searcher.search_merge(all_search_results)
    
    total_before_merge = sum(len(results) for results in all_search_results)
    print(f"   Total articles before merge: {total_before_merge}")
    print(f"   Unique articles after merge: {len(merged_results)}")
    print(f"   Duplicates removed: {total_before_merge - len(merged_results)}")
    
    # Example 5: Show details of first few articles
    print("\n5. Sample article details:")
    print("-" * 30)
    for i, article in enumerate(merged_results[:3], 1):
        print(f"\nArticle {i}:")
        print(f"   PMID: {article.pmid}")
        print(f"   Title: {article.title[:80]}...")
        print(f"   Authors: {', '.join(article.authors[:2])}...")
        print(f"   Journal: {article.journal}")
        print(f"   Date: {article.publication_date}")
        print(f"   Abstract: {article.abstract[:150]}...")
        if article.keywords:
            print(f"   Keywords: {', '.join(article.keywords[:3])}...")
    
    # Example 6: Get and display statistics
    print("\n6. Search Statistics:")
    print("-" * 20)
    stats = searcher.get_search_statistics(merged_results)
    print(f"   Total articles: {stats['total_articles']}")
    print(f"   Articles with abstracts: {stats['articles_with_abstracts']}")
    print(f"   Articles with DOI: {stats['articles_with_doi']}")
    print(f"   Total keywords: {stats['total_keywords']}")
    
    if stats['articles_by_year']:
        print("\n   Articles by year:")
        for year, count in sorted(stats['articles_by_year'].items(), reverse=True)[:5]:
            print(f"     {year}: {count}")
    
    if stats['top_journals']:
        print("\n   Top journals:")
        for journal, count in list(stats['top_journals'].items())[:3]:
            print(f"     {journal}: {count}")
    
    # Example 7: Export results
    output_file = "pubmed_search_results.csv"
    print(f"\n7. Exporting results to {output_file}...")
    searcher.export_to_csv(merged_results, output_file)
    print(f"   ✅ Results exported successfully!")
    
    print("\n" + "=" * 50)
    print("🎉 PubMed search example completed!")
    print(f"📁 Check {output_file} for detailed results")


def advanced_query_examples():
    """Show examples of advanced PubMed queries"""
    print("\n📚 Advanced Query Examples:")
    print("-" * 30)
    
    examples = [
        ("Basic keyword search", "covid-19 AND vaccine"),
        ("Title/Abstract search", "machine learning[Title/Abstract] AND diagnosis"),
        ("Author search", "smith j[Author] AND cancer"),
        ("Journal search", "nature[Journal] AND genetics"),
        ("MeSH terms", "Diabetes Mellitus[MeSH] AND diet therapy[MeSH]"),
        ("Date range", "covid-19 AND 2020:2023[PDat]"),
        ("Publication type", "covid-19 AND clinical trial[Publication Type]"),
        ("Field combinations", "cancer[Title] AND therapy[Abstract] AND human[MeSH]"),
        ("Complex query", "(covid-19 OR SARS-CoV-2) AND (vaccine OR vaccination) AND efficacy"),
        ("Recent articles", "artificial intelligence AND last 2 years[PDat]")
    ]
    
    for description, query in examples:
        print(f"   {description}:")
        print(f"     {query}")
        print()


if __name__ == "__main__":
    # Show advanced query examples first
    advanced_query_examples()
    
    # Run the main example
    main()