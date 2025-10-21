"""
DOI Downloader Usage Example

This example demonstrates how to use the DOI Downloader tool to download
academic papers. The tool first tries direct download from DOI URLs,
then falls back to Sci-Hub if needed.

Run this example with:
    python doi_example.py

Make sure to set the NCBI_EMAIL environment variable if integrating with PubMed.
Optionally set DOI_PDFS_DIR to specify download location.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from budapest_hackathlon.tools.doi_downloader import DOIDownloader, DownloadResult
except ImportError:
    # Try relative import if absolute doesn't work
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from doi_downloader import DOIDownloader, DownloadResult

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_single_download():
    """Example: Download a single paper by DOI."""
    print("\n=== Single DOI Download Example ===")
    
    # Initialize downloader
    downloader = DOIDownloader()
    
    # Example DOI (replace with actual DOI you want to download)
    doi = "10.1371/journal.pone.0000000"  # Example open access DOI
    title = "Example research paper"
    
    print(f"Downloading DOI: {doi}")
    print("Method: First try direct DOI URL, then fallback to sci-hub")
    
    # Download the paper
    result = downloader.download_doi(
        doi=doi,
        title=title,
        overwrite=False  # Don't overwrite if already exists
    )
    
    # Check result
    if result.success:
        print(f"✅ Successfully downloaded: {result.file_path}")
        print(f"Source: {result.source}")
        if result.source == "direct_doi" or result.source == "doi_redirect":
            print("🎉 Downloaded directly from publisher!")
        elif result.source == "sci-hub":
            print("📚 Downloaded via sci-hub fallback")
    else:
        print(f"❌ Download failed: {result.error_message}")
    
    return result

def example_batch_download():
    """Example: Download multiple papers in batch."""
    print("\n=== Batch DOI Download Example ===")
    
    # Initialize downloader with custom settings
    downloader = DOIDownloader(
        download_dir="./example_downloads",  # Custom download directory
        rate_limit_delay=2.0  # 2 seconds between downloads
    )
    
    # Example DOIs (replace with actual DOIs)
    dois = [
        "10.1038/nature12373",
        "10.1126/science.1234567",
        "10.1016/j.cell.2020.01.001"
    ]
    
    # Optional titles for better filenames
    titles = [
        "Deep learning paper",
        "Science breakthrough",
        "Cell biology research"
    ]
    
    print(f"Downloading {len(dois)} papers...")
    
    # Download all papers
    results = downloader.download_dois_batch(
        dois=dois,
        titles=titles,
        overwrite=False
    )
    
    # Print results
    for result in results:
        if result.success:
            print(f"✅ {result.doi}: {result.file_path}")
        else:
            print(f"❌ {result.doi}: {result.error_message}")
    
    # Get statistics
    stats = downloader.get_download_statistics(results)
    print(f"\nDownload Statistics:")
    print(f"Total attempted: {stats['total_attempted']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Sources used: {stats['sources']}")
    if stats['error_types']:
        print(f"Error types: {stats['error_types']}")
    
    return results

def example_integration_with_pubmed():
    """Example: Integration with PubMed search results."""
    print("\n=== PubMed Integration Example ===")
    
    try:
        # Import PubMed searcher
        try:
            from budapest_hackathlon.tools.pubmed.pubmed_search import PubMedSearcher
        except ImportError:
            # Try alternative import path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from budapest_hackathlon.tools.pubmed.pubmed_search import PubMedSearcher
        
        # Initialize both tools
        pubmed = PubMedSearcher()
        downloader = DOIDownloader()
        
        # Search for papers
        query = "machine learning AND healthcare"
        search_results = pubmed.search(query, max_results=5)
        
        print(f"Found {len(search_results)} papers from PubMed search")
        
        # Extract DOIs from search results
        dois_to_download = []
        titles_to_download = []
        
        for article in search_results:
            if article.doi:  # Only download papers with DOIs
                dois_to_download.append(article.doi)
                titles_to_download.append(article.title)
                print(f"Found DOI: {article.doi}")
        
        if dois_to_download:
            print(f"\nDownloading {len(dois_to_download)} papers with DOIs...")
            
            # Download the papers
            results = downloader.download_dois_batch(
                dois=dois_to_download,
                titles=titles_to_download
            )
            
            # Show results
            successful = sum(1 for r in results if r.success)
            print(f"Downloaded {successful}/{len(results)} papers successfully")
            
        else:
            print("No papers with DOIs found in search results")
            
    except ImportError:
        print("PubMed module not available. Skipping integration example.")
    except Exception as e:
        print(f"Error in PubMed integration: {e}")

def example_list_downloads():
    """Example: List downloaded files."""
    print("\n=== List Downloaded Files Example ===")
    
    downloader = DOIDownloader()
    
    files = downloader.list_downloaded_files()
    
    if files:
        print(f"Found {len(files)} downloaded PDF files:")
        for file_info in files[:10]:  # Show first 10
            print(f"📄 {file_info['filename']}")
            print(f"   Size: {file_info['size_mb']:.2f} MB")
            print(f"   Path: {file_info['path']}")
            print()
    else:
        print("No downloaded PDF files found")

def main():
    """Run all examples."""
    print("DOI Downloader Tool - Usage Examples")
    print("===================================")
    
    # Check environment
    download_dir = os.getenv("DOI_PDFS_DIR", "./doi_pdfs")
    print(f"Download directory: {download_dir}")
    
    try:
        # Run examples (commented out to avoid actual downloads during testing)
        # Uncomment the lines below to test actual downloads
        
        # example_single_download()
        # example_batch_download()
        # example_integration_with_pubmed()
        example_list_downloads()
        
        print("\n✅ Examples completed!")
        print("\nTo run actual downloads, uncomment the example functions in main()")
        print("Note: Actual downloads require internet connection and may take time")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()