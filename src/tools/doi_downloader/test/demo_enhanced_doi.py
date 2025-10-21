#!/usr/bin/env python3
"""
Demo script showing the enhanced DOI downloader functionality.

This script demonstrates the two-step download process:
1. First try direct download from DOI URL
2. Fall back to sci-hub if direct method fails

Usage:
    python demo_enhanced_doi.py
"""

import logging
import sys
from pathlib import Path

# Set up logging to see the process
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from budapest_hackathlon.tools.doi_downloader.doi_downloader import DOIDownloader

def demo_enhanced_downloader():
    """Demonstrate the enhanced DOI downloader."""
    print("🔬 Enhanced DOI Downloader Demo")
    print("=" * 40)
    print()
    print("This tool now uses a two-step process:")
    print("1. 🌐 Try direct download from DOI URL")
    print("2. 📚 Fall back to sci-hub if needed")
    print()
    
    # Initialize downloader
    downloader = DOIDownloader(
        download_dir="./demo_downloads",
        timeout=10,
        rate_limit_delay=1.0
    )
    
    # Test DOIs - mix of potentially accessible and restricted
    test_dois = [
        {
            "doi": "10.1371/journal.pone.0000001",
            "title": "PLoS ONE First Paper",
            "note": "Open access - should work with direct method"
        },
        {
            "doi": "10.1038/nature12373", 
            "title": "Nature Paper",
            "note": "Likely restricted - will try direct then sci-hub"
        }
    ]
    
    print(f"📋 Testing {len(test_dois)} DOIs...")
    print()
    
    for i, paper in enumerate(test_dois, 1):
        print(f"Test {i}: {paper['doi']}")
        print(f"Title: {paper['title']}")
        print(f"Note: {paper['note']}")
        print("-" * 40)
        
        # Attempt download
        result = downloader.download_doi(
            doi=paper['doi'],
            title=paper['title'],
            overwrite=True  # For demo purposes
        )
        
        # Show results
        if result.success:
            print(f"✅ SUCCESS!")
            print(f"   Method: {result.source}")
            print(f"   File: {result.file_path}")
            
            if result.source in ["direct_doi", "doi_redirect"]:
                print(f"   🎉 Direct download from publisher!")
            elif result.source == "sci-hub":
                print(f"   📚 Downloaded via sci-hub fallback")
            elif result.source == "cached":
                print(f"   💾 File was already cached")
                
            # Check file validity
            if result.file_path:
                file_path = Path(result.file_path)
                if file_path.exists():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    print(f"   📄 File size: {size_mb:.2f} MB")
                    
                    # Quick PDF validation
                    try:
                        with open(file_path, 'rb') as f:
                            header = f.read(4)
                            if header == b'%PDF':
                                print(f"   ✓ Valid PDF format")
                            else:
                                print(f"   ⚠️  May not be valid PDF")
                    except:
                        print(f"   ⚠️  Could not validate file")
        else:
            print(f"❌ FAILED")
            print(f"   Error: {result.error_message}")
        
        print()
    
    # Show final statistics
    print("📊 Final Statistics:")
    print("-" * 20)
    files = downloader.list_downloaded_files()
    print(f"Total downloaded files: {len(files)}")
    
    if files:
        total_size = sum(f['size_mb'] for f in files)
        print(f"Total size: {total_size:.2f} MB")
        print("\nDownloaded files:")
        for file_info in files:
            print(f"  📄 {file_info['filename']} ({file_info['size_mb']:.2f} MB)")
    
    print()
    print("🏁 Demo completed!")
    print()
    print("Key benefits of the enhanced downloader:")
    print("• ✅ Tries legitimate publisher sources first")
    print("• ✅ Respects open access policies")
    print("• ✅ Falls back to sci-hub only when needed")
    print("• ✅ Provides detailed source information")
    print("• ✅ Handles various publisher formats")

if __name__ == "__main__":
    try:
        demo_enhanced_downloader()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        import traceback
        traceback.print_exc()