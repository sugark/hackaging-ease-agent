#!/usr/bin/env python3
"""
PubMed Article PDF Downloader

This script downloads PDF files for articles that have been filtered as good candidates
for meta-analysis. It uses PMC Open Access API as the primary method and falls back
to DOI-based downloading when needed.

Author: Budapest Hackathlon Team
Date: October 2025
"""

import json
import os
import sys
import logging
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import time
from datetime import datetime

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('_pubmed_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the tools directory to the path to import DOI downloader
script_dir = Path(__file__).parent

# Try different possible locations for the DOI downloader
doi_downloader_paths = [
    script_dir / "tools" / "doi_downloader",
    script_dir.parent / "budapest_hackathlon" / "tools" / "doi_downloader",
    script_dir.parent / "budapest_hackathlon" / "tools",
]

DOIDownloader = None
DownloadResult = None

for path in doi_downloader_paths:
    if path.exists():
        sys.path.insert(0, str(path.parent))
        try:
            from doi_downloader.doi_downloader import DOIDownloader, DownloadResult
            logger.info(f"Successfully imported DOI downloader from: {path.parent}")
            break
        except ImportError:
            continue

# If DOI downloader is not available, we'll create a minimal fallback
if DOIDownloader is None:
    logger.warning("DOI downloader not available, using fallback implementation")
    
    class DownloadResult:
        def __init__(self, doi: str, success: bool, file_path: str = None, error_message: str = None, source: str = None):
            self.doi = doi
            self.success = success
            self.file_path = file_path
            self.error_message = error_message
            self.source = source
    
    class DOIDownloader:
        def __init__(self, download_dir: str = None):
            self.download_dir = Path(download_dir) if download_dir else Path(".")
            logger.warning("Using fallback DOI downloader - limited functionality")
        
        def download_doi(self, doi: str, title: str = None, custom_filename: str = None, overwrite: bool = False) -> DownloadResult:
            return DownloadResult(
                doi=doi,
                success=False,
                error_message="DOI downloader tool not available - please install or configure it"
            )


class PMCDownloader:
    """Class for downloading PDFs from PMC Open Access."""
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """Initialize PMC downloader with rate limiting."""
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_pmc_pdf_url(self, pmc_id: str) -> Optional[str]:
        """
        Get PDF download URL from PMC Open Access API.
        
        Args:
            pmc_id: PMC identifier (e.g., "PMC5334499")
            
        Returns:
            PDF download URL if available, None otherwise
        """
        try:
            # Ensure PMC ID has PMC prefix
            if not pmc_id.startswith('PMC'):
                pmc_id = f'PMC{pmc_id}'
            
            # Query PMC Open Access API
            api_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmc_id}"
            logger.info(f"Querying PMC API for {pmc_id}: {api_url}")
            
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Look for PDF links
            pdf_links = []
            for record in root.findall('.//record'):
                for link in record.findall('.//link[@format="pdf"]'):
                    href = link.get('href')
                    if href:
                        pdf_links.append(href)
                        logger.info(f"Found PDF link for {pmc_id}: {href}")
            
            if pdf_links:
                return pdf_links[0]  # Return the first PDF link
            else:
                logger.warning(f"No PDF links found for {pmc_id}")
                return None
                
        except ET.ParseError as e:
            logger.error(f"XML parsing error for {pmc_id}: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error querying PMC API for {pmc_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying PMC API for {pmc_id}: {e}")
            return None
    
    def download_pdf_from_url(self, pdf_url: str, file_path: Path) -> bool:
        """
        Download PDF from a given URL.
        
        Args:
            pdf_url: URL of the PDF to download
            file_path: Path where to save the PDF
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            
            response = self.session.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Check if content is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' not in content_type:
                # Check first few bytes for PDF magic number
                first_chunk = next(response.iter_content(chunk_size=1024), b'')
                if not first_chunk.startswith(b'%PDF'):
                    logger.warning(f"URL does not appear to contain a PDF: {pdf_url}")
                    return False
            
            # Download the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify file was written and has content
            if file_path.exists() and file_path.stat().st_size > 0:
                logger.info(f"Successfully downloaded PDF: {file_path}")
                return True
            else:
                logger.error(f"Downloaded file is empty or missing: {file_path}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Network error downloading {pdf_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {pdf_url}: {e}")
            return False


class PubMedPDFDownloader:
    """Main class for downloading PubMed article PDFs."""
    
    def __init__(self, download_dir: str = "downloaded_articles"):
        """
        Initialize the PubMed PDF downloader.
        
        Args:
            download_dir: Directory to save downloaded PDFs
        """
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.pmc_downloader = PMCDownloader()
        self.doi_downloader = DOIDownloader(download_dir=str(self.download_dir))
        
        logger.info(f"PubMed PDF Downloader initialized. Download directory: {self.download_dir}")
    
    def load_filtered_articles(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load filtered articles that are good candidates.
        
        Args:
            file_path: Path to _pubmed_filtered_articles.json
            
        Returns:
            List of good candidate articles
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            good_candidates = [
                article for article in data['classifications']
                if article.get('is_good_candidate', False)
            ]
            
            logger.info(f"Loaded {len(good_candidates)} good candidate articles from {file_path}")
            return good_candidates
            
        except Exception as e:
            logger.error(f"Error loading filtered articles from {file_path}: {e}")
            return []
    
    def load_fetched_metadata(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Load fetched metadata to get DOI and PMC information.
        
        Args:
            file_path: Path to _pubmed_fetched_meta_results.json
            
        Returns:
            Dictionary mapping PMID to article metadata
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create PMID to metadata mapping
            metadata_map = {}
            for article in data.get('articles', []):
                pmid = article.get('pmid')
                if pmid:
                    metadata_map[pmid] = article
            
            logger.info(f"Loaded metadata for {len(metadata_map)} articles from {file_path}")
            return metadata_map
            
        except Exception as e:
            logger.error(f"Error loading fetched metadata from {file_path}: {e}")
            return {}
    
    def merge_article_data(
        self,
        filtered_articles: List[Dict[str, Any]],
        metadata_map: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge filtered articles with their metadata.
        
        Args:
            filtered_articles: List of good candidate articles
            metadata_map: Dictionary mapping PMID to metadata
            
        Returns:
            List of merged article data
        """
        merged_articles = []
        
        for article in filtered_articles:
            pmid = article.get('pmid')
            if pmid and pmid in metadata_map:
                # Merge the data
                merged_article = {
                    **metadata_map[pmid],  # Start with metadata
                    **article,  # Add classification data
                    'download_status': 'pending',
                    'download_method': None,
                    'pdf_path': None,
                    'download_error': None
                }
                merged_articles.append(merged_article)
            else:
                logger.warning(f"No metadata found for PMID: {pmid}")
                # Still include the article but mark as incomplete
                merged_article = {
                    **article,
                    'download_status': 'no_metadata',
                    'download_method': None,
                    'pdf_path': None,
                    'download_error': 'No metadata available'
                }
                merged_articles.append(merged_article)
        
        logger.info(f"Merged data for {len(merged_articles)} articles")
        return merged_articles
    
    def generate_pdf_filename(self, article: Dict[str, Any]) -> str:
        """
        Generate a safe filename for the PDF.
        
        Args:
            article: Article data dictionary
            
        Returns:
            Safe filename for the PDF
        """
        pmid = article.get('pmid', 'unknown')
        title = article.get('title', '')
        
        # Sanitize title for filename
        if title:
            # Keep only alphanumeric characters, spaces, and some punctuation
            import re
            title_clean = re.sub(r'[<>:"/\\|?*]', '_', title)
            title_clean = re.sub(r'\s+', '_', title_clean.strip())
            # Limit length
            if len(title_clean) > 60:
                title_clean = title_clean[:60].rstrip('_')
            filename = f"{pmid}_{title_clean}.pdf"
        else:
            filename = f"{pmid}.pdf"
        
        return filename
    
    def download_article_pdf(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download PDF for a single article.
        
        Args:
            article: Article data dictionary
            
        Returns:
            Updated article dictionary with download results
        """
        pmid = article.get('pmid')
        pmc_id = article.get('pmc')
        doi = article.get('doi')
        
        logger.info(f"Attempting to download PDF for PMID: {pmid}")
        
        # Generate filename
        filename = self.generate_pdf_filename(article)
        file_path = self.download_dir / filename
        
        # Check if file already exists
        if file_path.exists():
            logger.info(f"PDF already exists for PMID {pmid}: {file_path}")
            article['download_status'] = 'already_exists'
            article['pdf_path'] = str(file_path)
            article['download_method'] = 'cached'
            return article
        
        # Method 1: Try PMC Open Access if PMC ID is available
        if pmc_id:
            logger.info(f"Attempting PMC download for PMID {pmid}, PMC ID: {pmc_id}")
            
            pdf_url = self.pmc_downloader.get_pmc_pdf_url(pmc_id)
            if pdf_url:
                success = self.pmc_downloader.download_pdf_from_url(pdf_url, file_path)
                if success:
                    article['download_status'] = 'success'
                    article['download_method'] = 'pmc_open_access'
                    article['pdf_path'] = str(file_path)
                    logger.info(f"Successfully downloaded via PMC: {pmid}")
                    return article
                else:
                    logger.warning(f"PMC download failed for PMID {pmid}")
            else:
                logger.warning(f"No PMC PDF URL found for PMID {pmid}")
        
        # Method 2: Try DOI download if DOI is available
        if doi:
            logger.info(f"Attempting DOI download for PMID {pmid}, DOI: {doi}")
            
            title = article.get('title')
            result = self.doi_downloader.download_doi(
                doi=doi,
                title=title,
                custom_filename=f"{pmid}_{title[:60] if title else 'article'}"
            )
            
            if result.success:
                # Move the file to our expected location if needed
                if result.file_path and Path(result.file_path).name != filename:
                    # DOI downloader might have used a different filename
                    doi_file_path = Path(result.file_path)
                    if doi_file_path.exists():
                        doi_file_path.rename(file_path)
                
                article['download_status'] = 'success'
                article['download_method'] = f'doi_{result.source}'
                article['pdf_path'] = str(file_path)
                logger.info(f"Successfully downloaded via DOI: {pmid}")
                return article
            else:
                logger.warning(f"DOI download failed for PMID {pmid}: {result.error_message}")
                article['download_error'] = result.error_message
        
        # Both methods failed
        error_msg = f"All download methods failed for PMID {pmid}"
        if not pmc_id and not doi:
            error_msg += " (no PMC ID or DOI available)"
        
        logger.error(error_msg)
        article['download_status'] = 'failed'
        article['download_error'] = error_msg
        
        return article
    
    def download_all_articles(
        self,
        articles: List[Dict[str, Any]],
        rate_limit_delay: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Download PDFs for all articles with rate limiting.
        
        Args:
            articles: List of article dictionaries
            rate_limit_delay: Delay between downloads in seconds
            
        Returns:
            List of updated article dictionaries with download results
        """
        total = len(articles)
        results = []
        
        logger.info(f"Starting download of {total} articles")
        
        for i, article in enumerate(articles, 1):
            pmid = article.get('pmid', 'unknown')
            logger.info(f"Processing article {i}/{total}: PMID {pmid}")
            
            # Download the article
            updated_article = self.download_article_pdf(article)
            results.append(updated_article)
            
            # Rate limiting
            if i < total:
                logger.info(f"Waiting {rate_limit_delay} seconds before next download...")
                time.sleep(rate_limit_delay)
        
        # Generate statistics
        successful = sum(1 for a in results if a.get('download_status') == 'success')
        cached = sum(1 for a in results if a.get('download_status') == 'already_exists')
        failed = sum(1 for a in results if a.get('download_status') == 'failed')
        
        logger.info(f"Download completed: {successful} successful, {cached} cached, {failed} failed out of {total} total")
        
        return results
    
    def save_results(self, articles: List[Dict[str, Any]], output_file: str = "_pubmed_downloaded_articles.json"):
        """
        Save the download results to a JSON file.
        
        Args:
            articles: List of article dictionaries with download results
            output_file: Output filename
        """
        output_path = Path(output_file)
        
        # Generate statistics
        total = len(articles)
        successful = sum(1 for a in articles if a.get('download_status') == 'success')
        cached = sum(1 for a in articles if a.get('download_status') == 'already_exists')
        failed = sum(1 for a in articles if a.get('download_status') == 'failed')
        no_metadata = sum(1 for a in articles if a.get('download_status') == 'no_metadata')
        
        # Count by download method
        methods = {}
        for article in articles:
            method = article.get('download_method')
            if method:
                methods[method] = methods.get(method, 0) + 1
        
        # Prepare output data
        output_data = {
            "metadata": {
                "total_articles": total,
                "successful_downloads": successful,
                "cached_files": cached,
                "failed_downloads": failed,
                "no_metadata": no_metadata,
                "download_methods": methods,
                "download_timestamp": datetime.now().isoformat(),
                "download_directory": str(self.download_dir)
            },
            "articles": articles
        }
        
        # Save to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {output_path}")
            logger.info(f"Statistics: {successful} successful, {cached} cached, {failed} failed")
            
        except Exception as e:
            logger.error(f"Error saving results to {output_path}: {e}")


def main():
    """
    Main function to run the download process.
    
    CLI Usage:
        python pubmed_download_articles.py
        
    Prerequisites:
        - _pubmed_filtered_articles.json (output from filtering step)
        - _pubmed_fetched_meta_results.json (output from metadata fetching step)
        
    Output:
        - _pubmed_downloaded_articles.json (download results and statistics)
        - downloaded_articles/ directory containing PDF files
        
    The script will:
        1. Load filtered articles marked as good candidates
        2. Load metadata including DOI and PMC information
        3. Attempt to download PDFs using PMC Open Access API first
        4. Fall back to DOI-based downloading if PMC fails
        5. Save results with download statistics
    """
    
    # File paths
    filtered_articles_file = "_pubmed_filtered_articles.json"
    metadata_file = "_pubmed_fetched_meta_results.json"
    output_file = "_pubmed_downloaded_articles.json"
    download_dir = "downloaded_articles"
    
    # Check if input files exist
    if not Path(filtered_articles_file).exists():
        logger.error(f"Filtered articles file not found: {filtered_articles_file}")
        return
    
    if not Path(metadata_file).exists():
        logger.error(f"Metadata file not found: {metadata_file}")
        return
    
    # Initialize downloader
    downloader = PubMedPDFDownloader(download_dir=download_dir)
    
    # Load data
    logger.info("Loading filtered articles...")
    filtered_articles = downloader.load_filtered_articles(filtered_articles_file)
    
    if not filtered_articles:
        logger.error("No good candidate articles found")
        return
    
    logger.info("Loading metadata...")
    metadata_map = downloader.load_fetched_metadata(metadata_file)
    
    if not metadata_map:
        logger.error("No metadata loaded")
        return
    
    # Merge data
    logger.info("Merging article data...")
    merged_articles = downloader.merge_article_data(filtered_articles, metadata_map)
    
    if not merged_articles:
        logger.error("No articles to download")
        return
    
    # Download articles
    logger.info(f"Starting download process for {len(merged_articles)} articles...")
    results = downloader.download_all_articles(merged_articles, rate_limit_delay=2.0)
    
    # Save results
    logger.info("Saving results...")
    downloader.save_results(results, output_file)
    
    logger.info("Download process completed!")


if __name__ == "__main__":
    main()