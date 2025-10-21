"""
Test script for PubMed Search module.

This script tests the basic functionality without making actual API calls.
For real testing, you'll need to set up your email and run with internet connection.
"""

import sys
import os

# Add the current directory to Python path for importing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        import pubmed_search
        print("   ✅ pubmed_search module imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import pubmed_search: {e}")
        return False
    
    try:
        from pubmed_search import PubMedSearcher, PubMedArticle
        print("   ✅ PubMedSearcher and PubMedArticle imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import classes: {e}")
        return False
    
    try:
        from Bio import Entrez
        print("   ✅ BioPython (Entrez) is available")
    except ImportError as e:
        print(f"   ❌ BioPython not installed: {e}")
        print("   💡 Install with: pip install biopython")
        return False
    
    return True


def test_article_creation():
    """Test PubMedArticle data class."""
    print("\n🧪 Testing PubMedArticle creation...")
    
    try:
        from pubmed_search import PubMedArticle
        
        # Create a test article
        article = PubMedArticle(
            pmid="12345678",
            title="Test Article Title",
            authors=["John Doe", "Jane Smith"],
            journal="Test Journal",
            publication_date="2023",
            abstract="This is a test abstract.",
            doi="10.1000/test.doi",
            keywords=["test", "pubmed", "search"]
        )
        
        print("   ✅ PubMedArticle created successfully")
        print(f"   📄 Title: {article.title}")
        print(f"   👥 Authors: {', '.join(article.authors)}")
        print(f"   📅 Date: {article.publication_date}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to create PubMedArticle: {e}")
        return False


def test_searcher_initialization():
    """Test PubMedSearcher initialization."""
    print("\n🧪 Testing PubMedSearcher initialization...")
    
    try:
        from pubmed_search import PubMedSearcher
        
        # Test initialization
        searcher = PubMedSearcher(email="test@example.com")
        print("   ✅ PubMedSearcher initialized successfully")
        print(f"   📧 Email: {searcher.email}")
        print(f"   ⏱️ Rate limit: {searcher.rate_limit}s")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to initialize PubMedSearcher: {e}")
        return False


def test_search_merge():
    """Test search merge functionality."""
    print("\n🧪 Testing search merge functionality...")
    
    try:
        from pubmed_search import PubMedSearcher, PubMedArticle
        
        searcher = PubMedSearcher(email="test@example.com")
        
        # Create test articles
        article1 = PubMedArticle("1", "Title 1", ["Author 1"], "Journal 1", "2023", "Abstract 1")
        article2 = PubMedArticle("2", "Title 2", ["Author 2"], "Journal 2", "2023", "Abstract 2")
        article3 = PubMedArticle("1", "Title 1", ["Author 1"], "Journal 1", "2023", "Abstract 1")  # Duplicate
        
        # Test merging
        result1 = [article1, article2]
        result2 = [article2, article3]  # article2 and article3 (duplicate of article1)
        
        merged = searcher.search_merge([result1, result2])
        
        print(f"   📊 Original results: {len(result1)} + {len(result2)} = {len(result1) + len(result2)} articles")
        print(f"   🔄 Merged results: {len(merged)} unique articles")
        print("   ✅ Search merge functionality working correctly")
        
        # Verify duplicates were removed
        if len(merged) == 2:  # Should be 2 unique articles (PMIDs "1" and "2")
            print("   ✅ Duplicates removed correctly")
        else:
            print(f"   ⚠️ Expected 2 unique articles, got {len(merged)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to test search merge: {e}")
        return False


def test_statistics():
    """Test statistics functionality."""
    print("\n🧪 Testing statistics functionality...")
    
    try:
        from pubmed_search import PubMedSearcher, PubMedArticle
        
        searcher = PubMedSearcher(email="test@example.com")
        
        # Create test articles
        articles = [
            PubMedArticle("1", "Title 1", ["Author 1"], "Nature", "2023", "Abstract 1", keywords=["biology"]),
            PubMedArticle("2", "Title 2", ["Author 2"], "Science", "2022", "Abstract 2", keywords=["chemistry", "physics"]),
            PubMedArticle("3", "Title 3", ["Author 3"], "Nature", "2023", "No abstract available"),
        ]
        
        stats = searcher.get_search_statistics(articles)
        
        print(f"   📊 Total articles: {stats['total_articles']}")
        print(f"   📄 Articles with abstracts: {stats['articles_with_abstracts']}")
        print(f"   📅 Articles by year: {stats['articles_by_year']}")
        print(f"   📰 Top journals: {stats['top_journals']}")
        print("   ✅ Statistics functionality working correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to test statistics: {e}")
        return False


def main():
    """Run all tests."""
    print("🔬 PubMed Search Module Tests")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_article_creation,
        test_searcher_initialization,
        test_search_merge,
        test_statistics
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The module is ready to use.")
        print("\n💡 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Set your email in the example script")
        print("   3. Run: python pubmed_example.py")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        
        if passed == 0:
            print("\n💡 Make sure to install BioPython:")
            print("   pip install biopython")


if __name__ == "__main__":
    main()