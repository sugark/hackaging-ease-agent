"""
DOI Downloader Tool for Budapest Hackathlon

This module provides functionality to download PDF papers using DOI identifiers.
It utilizes the scidownl library for accessing Sci-Hub and other sources.

Author: Budapest Hackathlon Team
Date: October 2025
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import re
import requests
import time
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        "BeautifulSoup4 library is required. Install with: pip install beautifulsoup4"
    )

try:
    from scidownl import scihub_download
except ImportError:
    raise ImportError(
        "scidownl library is required. Install with: pip install scidownl"
    )

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a DOI download attempt."""
    doi: str
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    source: Optional[str] = None


class DOIDownloader:
    """
    A class for downloading PDF papers using DOI identifiers.
    
    Uses scidownl library to access Sci-Hub and other academic paper sources.
    Downloads are saved to a configurable directory with organized naming.
    """
    
    def __init__(
        self,
        download_dir: Optional[str] = None,
        timeout: int = 30,
        rate_limit_delay: float = 1.0,
        max_redirects: int = 10
    ):
        """
        Initialize the DOI downloader.
        
        Args:
            download_dir: Directory to save downloaded PDFs. 
                         Defaults to DOI_PDFS_DIR env var or "./doi_pdfs"
            timeout: Timeout for download requests in seconds
            rate_limit_delay: Delay between downloads to be respectful
            max_redirects: Maximum number of redirects to follow
        """
        self.download_dir = self._get_download_directory(download_dir)
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.max_redirects = max_redirects
        
        # Create download directory if it doesn't exist
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up requests session with common headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        logger.info(f"DOI Downloader initialized. Download directory: {self.download_dir}")
    
    def _get_download_directory(self, download_dir: Optional[str] = None) -> Path:
        """
        Get the download directory from various sources.
        
        Priority: parameter > DOI_PDFS_DIR env var > ./doi_pdfs default
        """
        if download_dir:
            return Path(download_dir).resolve()
        
        env_dir = os.getenv("DOI_PDFS_DIR")
        if env_dir:
            return Path(env_dir).resolve()
        
        return Path("./doi_pdfs").resolve()
    
    def _sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """
        Sanitize text for use as filename.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length of resulting filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', text)
        # Remove extra spaces and replace with underscores
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip('_')
        
        return sanitized
    
    def _generate_filename(self, doi: str, title: Optional[str] = None) -> str:
        """
        Generate a filename for the PDF based on DOI and optional title.
        
        Args:
            doi: DOI identifier
            title: Optional paper title for more descriptive filename
            
        Returns:
            Generated filename with .pdf extension
        """
        # Clean DOI for filename use
        doi_clean = self._sanitize_filename(doi.replace("/", "_"))
        
        if title:
            title_clean = self._sanitize_filename(title, max_length=60)
            filename = f"{title_clean}_{doi_clean}.pdf"
        else:
            filename = f"{doi_clean}.pdf"
        
        return filename
    
    def _download_from_doi_url(self, doi: str, file_path: Path) -> DownloadResult:
        """
        Attempt to download PDF directly from DOI URL by following redirects
        and checking for PDF links in the HTML content.
        
        Args:
            doi: DOI identifier
            file_path: Path where to save the PDF file
            
        Returns:
            DownloadResult with success status and details
        """
        logger.info(f"Attempting direct download from DOI URL for: {doi}")
        
        try:
            # Start with the DOI URL
            doi_url = f"https://doi.org/{doi}"
            
            # Follow redirects and get the final page
            response = self.session.get(
                doi_url,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                return DownloadResult(
                    doi=doi,
                    success=False,
                    error_message=f"Failed to access DOI URL: HTTP {response.status_code}"
                )
            
            # Check if the response itself is a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' in content_type:
                logger.info(f"Direct PDF response for DOI: {doi}")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return DownloadResult(
                    doi=doi,
                    success=True,
                    file_path=str(file_path),
                    source="direct_doi"
                )
            
            # Parse HTML to look for PDF links
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.content, 'html.parser')
                pdf_url = self._find_pdf_link(soup, response.url)
                
                if pdf_url:
                    return self._download_pdf_from_url(pdf_url, file_path, doi, "doi_redirect")
            
            return DownloadResult(
                doi=doi,
                success=False,
                error_message="No PDF link found on publisher page"
            )
            
        except requests.RequestException as e:
            return DownloadResult(
                doi=doi,
                success=False,
                error_message=f"Network error accessing DOI: {str(e)}"
            )
        except Exception as e:
            return DownloadResult(
                doi=doi,
                success=False,
                error_message=f"Error in direct DOI download: {str(e)}"
            )
    
    def _find_pdf_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Find PDF download links in HTML content.
        
        Args:
            soup: BeautifulSoup object of the HTML page
            base_url: Base URL for resolving relative links
            
        Returns:
            PDF URL if found, None otherwise
        """
        # Common patterns for PDF links
        pdf_patterns = [
            # Direct PDF links
            r'\.pdf$',
            # Common PDF URL patterns
            r'/pdf/',
            r'getPDF',
            r'downloadPdf',
            r'viewPDF',
            r'article.*pdf',
            r'full.*pdf'
        ]
        
        # Look for links with PDF-related attributes
        pdf_selectors = [
            'a[href*=".pdf"]',
            'a[href*="/pdf/"]',
            'a[href*="getPDF"]',
            'a[href*="downloadPdf"]',
            'a[href*="viewPDF"]',
            'a[data-track-action*="PDF"]',
            'a[title*="PDF"]',
            'a[title*="pdf"]',
            'a.pdf-download',
            'a.download-pdf',
            '.pdf-link a',
            '.download-link a[href*="pdf"]'
        ]
        
        for selector in pdf_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    pdf_url = urljoin(base_url, href)
                    
                    # Check if it looks like a PDF URL
                    if any(re.search(pattern, pdf_url, re.IGNORECASE) for pattern in pdf_patterns):
                        logger.info(f"Found potential PDF link: {pdf_url}")
                        return pdf_url
        
        # Alternative: look for meta tags or specific publisher patterns
        meta_pdf = soup.find('meta', {'name': 'citation_pdf_url'})
        if meta_pdf and meta_pdf.get('content'):
            pdf_url = urljoin(base_url, meta_pdf['content'])
            logger.info(f"Found PDF via meta citation: {pdf_url}")
            return pdf_url
        
        return None
    
    def _download_pdf_from_url(self, pdf_url: str, file_path: Path, doi: str, source: str) -> DownloadResult:
        """
        Download PDF from a specific URL.
        
        Args:
            pdf_url: URL of the PDF to download
            file_path: Path where to save the PDF file
            doi: DOI identifier for logging
            source: Source identifier for the result
            
        Returns:
            DownloadResult with success status and details
        """
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            
            response = self.session.get(pdf_url, timeout=self.timeout)
            
            if response.status_code == 200:
                # Verify it's actually a PDF
                content_type = response.headers.get('content-type', '').lower()
                content = response.content
                
                # Check PDF magic bytes or content type
                if ('application/pdf' in content_type or 
                    content.startswith(b'%PDF')):
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    logger.info(f"Successfully downloaded PDF: {doi} -> {file_path}")
                    return DownloadResult(
                        doi=doi,
                        success=True,
                        file_path=str(file_path),
                        source=source
                    )
                else:
                    return DownloadResult(
                        doi=doi,
                        success=False,
                        error_message=f"URL did not return a valid PDF: {pdf_url}"
                    )
            else:
                return DownloadResult(
                    doi=doi,
                    success=False,
                    error_message=f"Failed to download from {pdf_url}: HTTP {response.status_code}"
                )
                
        except Exception as e:
            return DownloadResult(
                doi=doi,
                success=False,
                error_message=f"Error downloading from {pdf_url}: {str(e)}"
            )
    
    def download_doi(
        self,
        doi: str,
        title: Optional[str] = None,
        custom_filename: Optional[str] = None,
        overwrite: bool = False
    ) -> DownloadResult:
        """
        Download a single PDF using its DOI.
        
        First attempts direct download from DOI URL, then falls back to sci-hub.
        
        Args:
            doi: DOI identifier (e.g., "10.1038/nature12373")
            title: Optional paper title for filename generation
            custom_filename: Custom filename (without extension)
            overwrite: Whether to overwrite existing files
            
        Returns:
            DownloadResult with success status and details
        """
        logger.info(f"Attempting to download DOI: {doi}")
        
        try:
            # Generate filename
            if custom_filename:
                filename = f"{self._sanitize_filename(custom_filename)}.pdf"
            else:
                filename = self._generate_filename(doi, title)
            
            file_path = self.download_dir / filename
            
            # Check if file already exists
            if file_path.exists() and not overwrite:
                logger.info(f"File already exists: {file_path}")
                return DownloadResult(
                    doi=doi,
                    success=True,
                    file_path=str(file_path),
                    source="cached"
                )
            
            # Method 1: Try direct download from DOI URL
            logger.info(f"Trying direct download from DOI URL for: {doi}")
            result = self._download_from_doi_url(doi, file_path)
            
            if result.success:
                logger.info(f"Successfully downloaded via direct DOI method: {doi}")
                return result
            else:
                logger.warning(f"Direct DOI download failed: {result.error_message}")
            
            # Method 2: Fall back to sci-hub download
            logger.info(f"Falling back to sci-hub download for: {doi}")
            try:
                scihub_download(
                    keyword=doi,
                    paper_type="doi",
                    out=str(file_path)  # Full path including filename
                )
                
                # Check if download was successful
                if file_path.exists():
                    logger.info(f"Successfully downloaded via sci-hub: {doi} -> {file_path}")
                    return DownloadResult(
                        doi=doi,
                        success=True,
                        file_path=str(file_path),
                        source="sci-hub"
                    )
                else:
                    error_msg = f"Sci-hub download completed but file not found: {doi}"
                    logger.error(error_msg)
                    return DownloadResult(
                        doi=doi,
                        success=False,
                        error_message=error_msg
                    )
                    
            except Exception as download_error:
                error_msg = f"Sci-hub download failed for {doi}: {str(download_error)}"
                logger.error(error_msg)
                return DownloadResult(
                    doi=doi,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Error downloading DOI {doi}: {str(e)}"
            logger.error(error_msg)
            return DownloadResult(
                doi=doi,
                success=False,
                error_message=error_msg
            )
    
    def download_dois_batch(
        self,
        dois: List[str],
        titles: Optional[List[str]] = None,
        overwrite: bool = False
    ) -> List[DownloadResult]:
        """
        Download multiple PDFs using their DOIs.
        
        Args:
            dois: List of DOI identifiers
            titles: Optional list of paper titles (same length as dois)
            overwrite: Whether to overwrite existing files
            
        Returns:
            List of DownloadResult objects
        """
        if titles and len(titles) != len(dois):
            raise ValueError("If provided, titles list must have same length as dois list")
        
        results = []
        total = len(dois)
        
        logger.info(f"Starting batch download of {total} DOIs")
        
        for i, doi in enumerate(dois):
            title = titles[i] if titles else None
            
            logger.info(f"Downloading {i+1}/{total}: {doi}")
            
            result = self.download_doi(doi, title=title, overwrite=overwrite)
            results.append(result)
            
            # Rate limiting - be respectful to servers
            if i < total - 1:  # Don't delay after the last download
                import time
                time.sleep(self.rate_limit_delay)
        
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch download completed: {successful}/{total} successful")
        
        return results
    
    def get_download_statistics(self, results: List[DownloadResult]) -> Dict[str, Any]:
        """
        Generate statistics from download results.
        
        Args:
            results: List of DownloadResult objects
            
        Returns:
            Dictionary with download statistics
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        
        # Count by source
        sources = {}
        for result in results:
            if result.success and result.source:
                sources[result.source] = sources.get(result.source, 0) + 1
        
        # Get error summary
        errors = {}
        for result in results:
            if not result.success and result.error_message:
                # Categorize errors
                error_type = "Unknown"
                if "timeout" in result.error_message.lower():
                    error_type = "Timeout"
                elif "not found" in result.error_message.lower():
                    error_type = "Not Found"
                elif "connection" in result.error_message.lower():
                    error_type = "Connection Error"
                
                errors[error_type] = errors.get(error_type, 0) + 1
        
        return {
            "total_attempted": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "sources": sources,
            "error_types": errors,
            "download_directory": str(self.download_dir)
        }
    
    def list_downloaded_files(self) -> List[Dict[str, Any]]:
        """
        List all PDF files in the download directory.
        
        Returns:
            List of dictionaries with file information
        """
        files = []
        
        for pdf_file in self.download_dir.glob("*.pdf"):
            file_info = {
                "filename": pdf_file.name,
                "path": str(pdf_file),
                "size_mb": pdf_file.stat().st_size / (1024 * 1024),
                "modified": pdf_file.stat().st_mtime
            }
            files.append(file_info)
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return files