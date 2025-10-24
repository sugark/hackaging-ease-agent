#!/usr/bin/env python3
"""
PDF Size Analysis Script

This script reads the _classified_articles.json file, extracts PDF paths from 
successfully downloaded articles, determines the page count for each PDF, 
and displays the results ordered by page count in descending order.

Usage:
    python test_pdf_size.py
    python test_pdf_size.py --input-file custom_articles.json
    python test_pdf_size.py --max-results 10

Dependencies:
    - PyPDF2 (for PDF page counting)
    - json (standard library)
    - pathlib (standard library)

Environment: 
    - Standard Python 3.x environment
"""

import json
import logging
import argparse
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import PyPDF2
except ImportError:
    logger.error("PyPDF2 is not installed. Please install it with: pip install PyPDF2")
    exit(1)


@dataclass
class PDFInfo:
    """Data class to store PDF information."""
    pmid: str
    title: str
    pdf_path: str
    page_count: int
    file_size_mb: float


class PDFAnalyzer:
    """Class to analyze PDF files from classified articles."""
    
    def __init__(self, input_file: str = "src/_classified_articles.json"):
        """
        Initialize the PDF analyzer.
        
        Args:
            input_file: Path to the classified articles JSON file
        """
        self.input_file = Path(input_file)
        self.pdf_results: List[PDFInfo] = []
        
    def load_classified_articles(self) -> Dict:
        """
        Load the classified articles JSON file.
        
        Returns:
            Dict containing the classified articles data
            
        Raises:
            FileNotFoundError: If the input file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
            
        logger.info(f"Loading classified articles from: {self.input_file}")
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            total_articles = data.get('metadata', {}).get('total_articles', 0)
            successful_downloads = data.get('metadata', {}).get('successful_downloads', 0)
            
            logger.info(f"Loaded {total_articles} total articles, {successful_downloads} successful downloads")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file: {e}")
            raise
    
    def get_pdf_page_count(self, pdf_path: str) -> Optional[int]:
        """
        Get the number of pages in a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Number of pages in the PDF, or None if unable to read
        """
        try:
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF file not found: {pdf_path}")
                return None
                
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
                
        except Exception as e:
            logger.warning(f"Failed to read PDF {pdf_path}: {e}")
            return None
    
    def get_file_size_mb(self, pdf_path: str) -> float:
        """
        Get the file size in megabytes.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            File size in megabytes
        """
        try:
            if os.path.exists(pdf_path):
                size_bytes = os.path.getsize(pdf_path)
                return round(size_bytes / (1024 * 1024), 2)
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to get file size for {pdf_path}: {e}")
            return 0.0
    
    def analyze_pdfs(self) -> None:
        """
        Analyze all PDFs from successfully downloaded articles.
        """
        data = self.load_classified_articles()
        articles = data.get('articles', [])
        
        logger.info("Analyzing PDFs from successfully downloaded articles...")
        
        successful_count = 0
        failed_count = 0
        
        for article in articles:
            # Only process articles with successful downloads
            if article.get('download_status') != 'success':
                continue
                
            pdf_path = article.get('pdf_path')
            if not pdf_path:
                logger.warning(f"No PDF path for article PMID: {article.get('pmid', 'unknown')}")
                failed_count += 1
                continue
            
            # Get page count
            page_count = self.get_pdf_page_count(pdf_path)
            if page_count is None:
                logger.warning(f"Failed to get page count for PMID: {article.get('pmid', 'unknown')}")
                failed_count += 1
                continue
            
            # Get file size
            file_size_mb = self.get_file_size_mb(pdf_path)
            
            # Create PDF info object
            pdf_info = PDFInfo(
                pmid=article.get('pmid', 'unknown'),
                title=article.get('title', 'Unknown Title')[:80] + '...' if len(article.get('title', '')) > 80 else article.get('title', 'Unknown Title'),
                pdf_path=pdf_path,
                page_count=page_count,
                file_size_mb=file_size_mb
            )
            
            self.pdf_results.append(pdf_info)
            successful_count += 1
            
            logger.debug(f"Processed PMID {pdf_info.pmid}: {page_count} pages, {file_size_mb} MB")
        
        logger.info(f"Analysis complete: {successful_count} PDFs processed successfully, {failed_count} failed")
    
    def display_results(self, max_results: Optional[int] = None) -> None:
        """
        Display the results ordered by page count in descending order.
        
        Args:
            max_results: Maximum number of results to display (None for all)
        """
        if not self.pdf_results:
            logger.warning("No PDF results to display")
            return
        
        # Sort by page count in descending order
        sorted_results = sorted(self.pdf_results, key=lambda x: x.page_count, reverse=True)
        
        # Limit results if specified
        if max_results:
            sorted_results = sorted_results[:max_results]
            logger.info(f"Displaying top {len(sorted_results)} results (limited to {max_results})")
        else:
            logger.info(f"Displaying all {len(sorted_results)} results")
        
        print("\n" + "="*120)
        print("PDF ANALYSIS RESULTS - Ordered by Page Count (Descending)")
        print("="*120)
        print(f"{'Rank':<5} {'PMID':<12} {'Pages':<7} {'Size(MB)':<10} {'Title':<50} {'PDF Path'}")
        print("-"*120)
        
        for idx, pdf_info in enumerate(sorted_results, 1):
            print(f"{idx:<5} {pdf_info.pmid:<12} {pdf_info.page_count:<7} {pdf_info.file_size_mb:<10} {pdf_info.title:<50} {pdf_info.pdf_path}")
        
        print("-"*120)
        
        # Display summary statistics
        total_pages = sum(pdf.page_count for pdf in self.pdf_results)
        total_size_mb = sum(pdf.file_size_mb for pdf in self.pdf_results)
        avg_pages = round(total_pages / len(self.pdf_results), 1) if self.pdf_results else 0
        avg_size_mb = round(total_size_mb / len(self.pdf_results), 2) if self.pdf_results else 0
        
        print(f"\nSUMMARY STATISTICS:")
        print(f"Total PDFs analyzed: {len(self.pdf_results)}")
        print(f"Total pages: {total_pages}")
        print(f"Total size: {total_size_mb:.2f} MB")
        print(f"Average pages per PDF: {avg_pages}")
        print(f"Average size per PDF: {avg_size_mb} MB")
        print(f"Largest PDF: {sorted_results[0].page_count} pages ({sorted_results[0].pmid})")
        print(f"Smallest PDF: {sorted_results[-1].page_count} pages ({sorted_results[-1].pmid})")


def main():
    """Entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Analyze PDF files from classified articles and display results ordered by page count',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all PDFs from default file
  python test_pdf_size.py
  
  # Use a different input file
  python test_pdf_size.py --input-file project_resveratrol_diabates2/_classified_articles.json
  
  # Show only top 10 largest PDFs
  python test_pdf_size.py --max-results 10
        """
    )
    
    parser.add_argument(
        '--input-file', 
        type=str, 
        default='_classified_articles.json',
        help='Path to the classified articles JSON file (default: _classified_articles.json)'
    )
    
    parser.add_argument(
        '--max-results',
        type=int,
        help='Maximum number of results to display (default: all)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize analyzer
        analyzer = PDFAnalyzer(args.input_file)
        
        # Analyze PDFs
        analyzer.analyze_pdfs()
        
        # Display results
        analyzer.display_results(args.max_results)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())