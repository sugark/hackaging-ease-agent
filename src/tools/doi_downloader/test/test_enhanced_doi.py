#!/usr/bin/env python3
"""
Test script for the enhanced DOI downloader that tries direct DOI URLs first.
"""

import logging
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from budapest_hackathlon.tools.doi_downloader.doi_downloader import DOIDownloader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_download():
    """Test the enhanced DOI downloader with direct URL method first."""
    print("🧪 Testing Enhanced DOI Downloader")
    print("=" * 50)
    
    # Initialize downloader
    downloader = DOIDownloader(
        download_dir="./test_downloads",
        timeout=15,
        rate_limit_delay=1.0
    )
    
    # Test with a known open access DOI that should be directly accessible
    test_dois = [
        "10.1371/journal.pone.0000001",  # PLoS ONE - usually open access
        "10.3389/fpsyg.2020.00001",      # Frontiers - open access
    ]
    
    for doi in test_dois:
        print(f"\n📄 Testing DOI: {doi}")
        print("-" * 30)
        
        # Attempt download
        result = downloader.download_doi(
            doi=doi,
            title=f"Test paper {doi}",
            overwrite=True  # Overwrite for testing
        )
        
        # Print results
        if result.success:
            print(f"✅ SUCCESS!")
            print(f"   Source: {result.source}")
            print(f"   File: {result.file_path}")
            
            # Check file size
            if result.file_path:
                file_path = Path(result.file_path)
                if file_path.exists():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    print(f"   Size: {size_mb:.2f} MB")
                    
                    # Quick check if it's a valid PDF
                    with open(file_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            print(f"   ✓ Valid PDF file")
                        else:
                            print(f"   ⚠️  File may not be a valid PDF")
        else:
            print(f"❌ FAILED: {result.error_message}")
    
    print(f"\n📊 Download Statistics:")
    files = downloader.list_downloaded_files()
    print(f"Total files downloaded: {len(files)}")
    
    return True

if __name__ == "__main__":
    try:
        test_enhanced_download()
        print("\n🎉 Test completed!")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()