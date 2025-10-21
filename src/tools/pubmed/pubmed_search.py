"""
PubMed Search Module

This module provides functionality to search PubMed articles using advanced queries
and retrieve article details including abstracts.

Required dependencies:
    - biopython: pip install biopython
    - requests: pip install requests (usually comes with Python)

Usage:
    from pubmed_search import PubMedSearcher
    
    searcher = PubMedSearcher(email="your.email@example.com")
    results = searcher.search("covid-19 AND vaccine")
    merged_results = searcher.search_merge([results1, results2, results3])
"""

from typing import List, Dict, Any, Union, Optional
import time
import logging
from dataclasses import dataclass
from collections import defaultdict

try:
    from Bio import Entrez
except ImportError:
    raise ImportError("BioPython is required. Install with: pip install biopython")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PubMedArticle:
    """Data class to represent a PubMed article"""
    pmid: str
    title: str
    authors: List[str]
    journal: str
    publication_date: str
    abstract: str
    pmc: Optional[str] = None
    doi: Optional[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class PubMedSearcher:
    """
    A class to search PubMed articles and retrieve detailed information.
    
    This class provides methods to:
    1. Search PubMed using advanced queries
    2. Retrieve article details including abstracts
    3. Merge multiple search results while removing duplicates
    """
    
    def __init__(self, email: str, api_key: Optional[str] = None, rate_limit: float = 0.34):
        """
        Initialize the PubMed searcher.
        
        Args:
            email (str): Your email address (required by NCBI)
            api_key (str, optional): NCBI API key for higher rate limits
            rate_limit (float): Delay between requests in seconds (default: 0.34s = ~3 requests/sec)
        """
        self.email = email
        self.api_key = api_key
        self.rate_limit = rate_limit
        
        # Configure Entrez
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
            
        logger.info(f"PubMedSearcher initialized with email: {email}")
    
    def search(self, query: str, max_results: int = 100, sort: str = "relevance") -> List[PubMedArticle]:
        """
        Search PubMed articles based on an advanced query.
        
        Args:
            query (str): Advanced PubMed query string
                Examples:
                - "covid-19 AND vaccine"
                - "cancer[Title] AND therapy[Abstract]"
                - "machine learning[MeSH Terms] AND radiology"
                - "author_name[Author] AND last_5_years[PDat]"
            max_results (int): Maximum number of results to retrieve (default: 100)
            sort (str): Sort order - "relevance", "pub_date", "author", "journal" (default: "relevance")
            
        Returns:
            List[PubMedArticle]: List of PubMed articles with details
        """
        try:
            logger.info(f"Searching PubMed with query: '{query}' (max_results: {max_results})")
            
            # Search for PMIDs
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort=sort
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            
            pmids = search_results["IdList"]
            logger.info(f"Found {len(pmids)} articles")
            
            if not pmids:
                logger.warning("No articles found for the given query")
                return []
            
            # Retrieve detailed information
            articles = self._fetch_article_details(pmids)
            
            logger.info(f"Successfully retrieved details for {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error during PubMed search: {str(e)}")
            raise
    
    def _fetch_article_details(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch detailed information for a list of PMIDs.
        
        Args:
            pmids (List[str]): List of PubMed IDs
            
        Returns:
            List[PubMedArticle]: List of articles with detailed information
        """
        articles = []
        
        # Process in batches to avoid overwhelming the server
        batch_size = 20
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            
            try:
                # Rate limiting
                time.sleep(self.rate_limit)
                
                # Fetch article details
                fetch_handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch_pmids),
                    rettype="medline",
                    retmode="xml"
                )
                records = Entrez.read(fetch_handle)
                fetch_handle.close()
                
                # Parse each article
                for record in records["PubmedArticle"]:
                    article = self._parse_article_record(record)
                    if article:
                        articles.append(article)
                        
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(pmids)-1)//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Error fetching batch {i//batch_size + 1}: {str(e)}")
                continue
        
        return articles
    
    def _parse_article_record(self, record: Dict[str, Any]) -> Optional[PubMedArticle]:
        """
        Parse a single PubMed article record.
        
        Args:
            record (Dict): Raw PubMed article record
            
        Returns:
            Optional[PubMedArticle]: Parsed article or None if parsing fails
        """
        try:
            medline_citation = record["MedlineCitation"]
            article_data = medline_citation["Article"]
            
            # Extract PMID
            pmid = str(medline_citation["PMID"])
            
            # Extract PMC ID
            pmc = self._extract_pmc(record)
            
            # Extract title
            title = article_data.get("ArticleTitle", "No title available")
            if isinstance(title, list):
                title = " ".join(str(t) for t in title)
            
            # Extract authors
            authors = []
            if "AuthorList" in article_data:
                for author in article_data["AuthorList"]:
                    if "LastName" in author and "ForeName" in author:
                        authors.append(f"{author['ForeName']} {author['LastName']}")
                    elif "CollectiveName" in author:
                        authors.append(author["CollectiveName"])
            
            # Extract journal
            journal = article_data.get("Journal", {}).get("Title", "Unknown journal")
            
            # Extract publication date
            pub_date = self._extract_publication_date(article_data)
            
            # Extract abstract
            abstract = self._extract_abstract(article_data)
            
            # Extract DOI
            doi = self._extract_doi(record)
            
            # Extract keywords
            keywords = self._extract_keywords(medline_citation)
            
            return PubMedArticle(
                pmid=pmid,
                title=title,
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                abstract=abstract,
                pmc=pmc,
                doi=doi,
                keywords=keywords
            )
            
        except Exception as e:
            logger.error(f"Error parsing article record: {str(e)}")
            return None
    
    def _extract_publication_date(self, article_data: Dict[str, Any]) -> str:
        """Extract publication date from article data."""
        try:
            journal_data = article_data.get("Journal", {})
            journal_issue = journal_data.get("JournalIssue", {})
            pub_date = journal_issue.get("PubDate", {})
            
            year = pub_date.get("Year", "")
            month = pub_date.get("Month", "")
            day = pub_date.get("Day", "")
            
            date_parts = [part for part in [year, month, day] if part]
            return " ".join(date_parts) if date_parts else "Unknown date"
            
        except:
            return "Unknown date"
    
    def _extract_abstract(self, article_data: Dict[str, Any]) -> str:
        """Extract abstract from article data."""
        try:
            abstract_data = article_data.get("Abstract", {})
            abstract_texts = abstract_data.get("AbstractText", [])
            
            if isinstance(abstract_texts, list):
                # Handle structured abstracts
                abstract_parts = []
                for text in abstract_texts:
                    if isinstance(text, dict) and "Label" in text:
                        label = text.get("Label", "")
                        content = str(text.get("#text", text))
                        abstract_parts.append(f"{label}: {content}" if label else content)
                    else:
                        abstract_parts.append(str(text))
                return " ".join(abstract_parts)
            else:
                return str(abstract_texts) if abstract_texts else "No abstract available"
                
        except:
            return "No abstract available"
    
    def _extract_doi(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract DOI from article record."""
        try:
            # Check in PubmedData section
            pubmed_data = record.get("PubmedData", {})
            article_ids = pubmed_data.get("ArticleIdList", [])
            
            for article_id in article_ids:
                # Handle both dict format and direct string format
                if isinstance(article_id, dict):
                    if article_id.get("IdType") == "doi":
                        return str(article_id.get("#text", article_id))
                elif hasattr(article_id, 'attributes') and hasattr(article_id, '__str__'):
                    # Handle BioPython parsed XML elements
                    if getattr(article_id, 'attributes', {}).get('IdType') == 'doi':
                        return str(article_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting DOI: {str(e)}")
            return None
    
    def _extract_pmc(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract PMC ID from article record."""
        try:
            # Check in PubmedData section
            pubmed_data = record.get("PubmedData", {})
            article_ids = pubmed_data.get("ArticleIdList", [])
            
            for article_id in article_ids:
                # Handle both dict format and direct string format
                if isinstance(article_id, dict):
                    if article_id.get("IdType") == "pmc":
                        pmc_id = str(article_id.get("#text", article_id))
                        # Ensure PMC ID has proper format
                        if not pmc_id.startswith("PMC"):
                            pmc_id = f"PMC{pmc_id}"
                        return pmc_id
                elif hasattr(article_id, 'attributes') and hasattr(article_id, '__str__'):
                    # Handle BioPython parsed XML elements
                    if getattr(article_id, 'attributes', {}).get('IdType') == 'pmc':
                        pmc_id = str(article_id)
                        if not pmc_id.startswith("PMC"):
                            pmc_id = f"PMC{pmc_id}"
                        return pmc_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting PMC ID: {str(e)}")
            return None
    
    def _extract_keywords(self, medline_citation: Dict[str, Any]) -> List[str]:
        """Extract keywords/MeSH terms from medline citation."""
        keywords = []
        
        try:
            # Extract MeSH headings
            mesh_list = medline_citation.get("MeshHeadingList", [])
            for mesh in mesh_list:
                descriptor = mesh.get("DescriptorName", {})
                if isinstance(descriptor, dict):
                    keywords.append(descriptor.get("#text", ""))
                else:
                    keywords.append(str(descriptor))
            
            # Extract keyword list if available
            keyword_list = medline_citation.get("KeywordList", [])
            for keyword_group in keyword_list:
                if isinstance(keyword_group, list):
                    for keyword in keyword_group:
                        keywords.append(str(keyword))
                        
        except:
            pass
        
        return [k for k in keywords if k]  # Remove empty keywords
    
    def search_merge(self, search_results: List[List[PubMedArticle]]) -> List[PubMedArticle]:
        """
        Merge multiple search results into a single distinct list.
        
        Args:
            search_results (List[List[PubMedArticle]]): List of search result lists
            
        Returns:
            List[PubMedArticle]: Merged list with duplicates removed
        """
        if not search_results:
            return []
        
        logger.info(f"Merging {len(search_results)} search result lists")
        
        # Use PMID to track unique articles
        unique_articles = {}
        total_articles = 0
        
        for result_list in search_results:
            total_articles += len(result_list)
            for article in result_list:
                # Use PMID as unique identifier
                if article.pmid not in unique_articles:
                    unique_articles[article.pmid] = article
        
        merged_list = list(unique_articles.values())
        
        logger.info(f"Merged {total_articles} total articles into {len(merged_list)} unique articles")
        logger.info(f"Removed {total_articles - len(merged_list)} duplicates")
        
        return merged_list
    
    def export_to_csv(self, articles: List[PubMedArticle], filename: str) -> None:
        """
        Export articles to CSV file.
        
        Args:
            articles (List[PubMedArticle]): List of articles to export
            filename (str): Output CSV filename
        """
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['pmid', 'pmc', 'title', 'authors', 'journal', 'publication_date', 
                         'abstract', 'doi', 'keywords']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for article in articles:
                writer.writerow({
                    'pmid': article.pmid,
                    'pmc': article.pmc or '',
                    'title': article.title,
                    'authors': '; '.join(article.authors),
                    'journal': article.journal,
                    'publication_date': article.publication_date,
                    'abstract': article.abstract,
                    'doi': article.doi or '',
                    'keywords': '; '.join(article.keywords)
                })
        
        logger.info(f"Exported {len(articles)} articles to {filename}")
    
    def export_to_json(self, articles: List[PubMedArticle], filename: str) -> None:
        """
        Export articles to JSON file.
        
        Args:
            articles (List[PubMedArticle]): List of articles to export
            filename (str): Output JSON filename
        """
        import json
        
        # Convert articles to dictionaries
        articles_data = []
        for article in articles:
            article_dict = {
                'pmid': article.pmid,
                'pmc': article.pmc,
                'title': article.title,
                'authors': article.authors,
                'journal': article.journal,
                'publication_date': article.publication_date,
                'abstract': article.abstract,
                'doi': article.doi,
                'keywords': article.keywords
            }
            articles_data.append(article_dict)
        
        # Create export data with metadata
        export_data = {
            'metadata': {
                'total_articles': len(articles),
                'export_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'PubMed via PubMedSearcher'
            },
            'articles': articles_data
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(articles)} articles to {filename}")
    
    def get_search_statistics(self, articles: List[PubMedArticle]) -> Dict[str, Any]:
        """
        Get statistics about search results.
        
        Args:
            articles (List[PubMedArticle]): List of articles
            
        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        if not articles:
            return {"total_articles": 0}
        
        # Count articles by year
        year_counts = defaultdict(int)
        journal_counts = defaultdict(int)
        
        for article in articles:
            # Extract year from publication date
            year = article.publication_date.split()[0] if article.publication_date else "Unknown"
            year_counts[year] += 1
            journal_counts[article.journal] += 1
        
        return {
            "total_articles": len(articles),
            "articles_by_year": dict(year_counts),
            "top_journals": dict(sorted(journal_counts.items(), 
                                      key=lambda x: x[1], reverse=True)[:10]),
            "articles_with_abstracts": sum(1 for a in articles 
                                         if a.abstract != "No abstract available"),
            "articles_with_doi": sum(1 for a in articles if a.doi),
            "articles_with_pmc": sum(1 for a in articles if a.pmc),
            "total_keywords": sum(len(a.keywords) for a in articles)
        }


# Example usage and utility functions
def example_usage():
    """Example of how to use the PubMedSearcher class."""
    
    # Initialize searcher (replace with your email)
    searcher = PubMedSearcher(email="your.email@example.com")
    
    # Single search
    results1 = searcher.search("covid-19 AND vaccine", max_results=50)
    print(f"Search 1 found {len(results1)} articles")
    
    # Another search
    results2 = searcher.search("SARS-CoV-2 AND immunization", max_results=30)
    print(f"Search 2 found {len(results2)} articles")
    
    # Merge results
    merged_results = searcher.search_merge([results1, results2])
    print(f"Merged results: {len(merged_results)} unique articles")
    
    # Get statistics
    stats = searcher.get_search_statistics(merged_results)
    print(f"Statistics: {stats}")
    
    # Export to CSV
    searcher.export_to_csv(merged_results, "pubmed_results.csv")
    
    # Print first article details
    if merged_results:
        article = merged_results[0]
        print(f"\nFirst article:")
        print(f"Title: {article.title}")
        print(f"Authors: {', '.join(article.authors[:3])}...")
        print(f"Journal: {article.journal}")
        print(f"Abstract: {article.abstract[:200]}...")


if __name__ == "__main__":
    example_usage()