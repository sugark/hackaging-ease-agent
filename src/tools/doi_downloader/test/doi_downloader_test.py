"""
DOI Downloader Test Suite

Unit tests for the DOI Downloader tool.
These tests can run offline and validate core functionality.

Run tests with:
    python doi_downloader_test.py
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from budapest_hackathlon.tools.doi_downloader.doi_downloader import (
        DOIDownloader, 
        DownloadResult
    )
except ImportError:
    # Try relative import if absolute doesn't work
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from doi_downloader import DOIDownloader, DownloadResult


class TestDOIDownloader(unittest.TestCase):
    """Test cases for DOI Downloader functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.downloader = DOIDownloader(download_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test DOIDownloader initialization."""
        # Test default initialization
        downloader = DOIDownloader()
        self.assertIsNotNone(downloader.download_dir)
        self.assertTrue(downloader.download_dir.exists())
        
        # Test custom directory
        custom_downloader = DOIDownloader(download_dir=self.test_dir)
        self.assertEqual(str(custom_downloader.download_dir), str(Path(self.test_dir).resolve()))
    
    def test_environment_variable_support(self):
        """Test environment variable for download directory."""
        test_env_dir = os.path.join(self.test_dir, "env_test")
        
        with patch.dict(os.environ, {"DOI_PDFS_DIR": test_env_dir}):
            downloader = DOIDownloader()
            self.assertEqual(str(downloader.download_dir), str(Path(test_env_dir).resolve()))
            self.assertTrue(downloader.download_dir.exists())
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test basic cases
        self.assertEqual(
            self.downloader._sanitize_filename("Normal Title"),
            "Normal_Title"
        )
        
        self.assertEqual(
            self.downloader._sanitize_filename("Title with / and \\"),
            "Title_with___and__"
        )
        
        self.assertEqual(
            self.downloader._sanitize_filename("Title with <special> chars: |?*"),
            "Title_with__special__chars_____"
        )
        
        self.assertEqual(
            self.downloader._sanitize_filename("  Spaces  Around  "),
            "Spaces_Around"
        )
        
        # Test length limiting
        long_title = "Very Long Title " * 20
        result = self.downloader._sanitize_filename(long_title)
        self.assertLessEqual(len(result), 100)  # Should be truncated
        self.assertTrue(result.startswith("Very_Long_Title"))
        self.assertFalse(result.endswith("_"))  # Should strip trailing underscores
    
    def test_generate_filename(self):
        """Test filename generation."""
        # Test with DOI only
        doi = "10.1038/nature12373"
        filename = self.downloader._generate_filename(doi)
        self.assertTrue(filename.endswith(".pdf"))
        self.assertIn("10.1038_nature12373", filename)
        
        # Test with DOI and title
        title = "A Great Scientific Paper"
        filename_with_title = self.downloader._generate_filename(doi, title)
        self.assertTrue(filename_with_title.endswith(".pdf"))
        self.assertIn("A_Great_Scientific_Paper", filename_with_title)
        self.assertIn("10.1038_nature12373", filename_with_title)
    
    @patch('requests.Session.get')
    @patch('doi_downloader.scihub_download')
    def test_download_doi_direct_method_success(self, mock_scihub_download, mock_requests_get):
        """Test successful direct DOI URL download."""
        # Mock direct DOI download success
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/pdf'}
        mock_response.content = b'%PDF-1.4 fake pdf content'
        mock_requests_get.return_value = mock_response
        
        doi = "10.1038/nature12373"
        result = self.downloader.download_doi(doi)
        
        # Should succeed with direct method, not call sci-hub
        self.assertTrue(result.success)
        self.assertEqual(result.doi, doi)
        self.assertEqual(result.source, "direct_doi")
        mock_scihub_download.assert_not_called()
    
    @patch('requests.Session.get')
    @patch('doi_downloader.scihub_download')
    def test_download_doi_fallback_to_scihub(self, mock_scihub_download, mock_requests_get):
        """Test fallback to sci-hub when direct method fails."""
        # Mock direct DOI download failure
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response
        
        # Mock successful sci-hub download
        doi = "10.1038/nature12373"
        expected_filename = self.downloader._generate_filename(doi)
        expected_path = self.downloader.download_dir / expected_filename
        
        def mock_download_side_effect(keyword, paper_type, out):
            Path(out).write_text("fake pdf content")
        
        mock_scihub_download.side_effect = mock_download_side_effect
        
        result = self.downloader.download_doi(doi)
        
        # Should fallback to sci-hub
        self.assertTrue(result.success)
        self.assertEqual(result.source, "sci-hub")
        mock_scihub_download.assert_called_once()
    
    def test_find_pdf_link(self):
        """Test PDF link finding in HTML content."""
        from bs4 import BeautifulSoup
        
        # Test HTML with direct PDF link
        html_with_pdf = """
        <html>
            <body>
                <a href="/download/paper.pdf">Download PDF</a>
                <a href="/other/link">Other Link</a>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html_with_pdf, 'html.parser')
        pdf_url = self.downloader._find_pdf_link(soup, "https://example.com")
        
        self.assertIsNotNone(pdf_url)
        self.assertIn("paper.pdf", pdf_url)
        self.assertTrue(pdf_url.startswith("https://example.com"))
    
    def test_find_pdf_link_meta_citation(self):
        """Test PDF link finding via meta citation."""
        from bs4 import BeautifulSoup
        
        html_with_meta = """
        <html>
            <head>
                <meta name="citation_pdf_url" content="/path/to/paper.pdf">
            </head>
            <body>
                <p>Content</p>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html_with_meta, 'html.parser')
        pdf_url = self.downloader._find_pdf_link(soup, "https://journal.com")
        
        self.assertIsNotNone(pdf_url)
        self.assertIn("paper.pdf", pdf_url)
        self.assertTrue(pdf_url.startswith("https://journal.com"))
    
    @patch('doi_downloader.scihub_download')
    def test_download_doi_failure(self, mock_scihub_download):
        """Test failed DOI download."""
        # Mock scidownl behavior - raise exception for failure
        mock_scihub_download.side_effect = Exception("Download failed")
        
        doi = "10.1038/invalid_doi"
        result = self.downloader.download_doi(doi)
        
        self.assertFalse(result.success)
        self.assertEqual(result.doi, doi)
        self.assertIsNotNone(result.error_message)
    
    def test_download_result_dataclass(self):
        """Test DownloadResult dataclass."""
        # Test successful result
        success_result = DownloadResult(
            doi="10.1038/nature12373",
            success=True,
            file_path="/path/to/file.pdf",
            source="sci-hub"
        )
        
        self.assertEqual(success_result.doi, "10.1038/nature12373")
        self.assertTrue(success_result.success)
        self.assertEqual(success_result.file_path, "/path/to/file.pdf")
        self.assertEqual(success_result.source, "sci-hub")
        
        # Test failed result
        fail_result = DownloadResult(
            doi="10.1038/invalid",
            success=False,
            error_message="Download failed"
        )
        
        self.assertEqual(fail_result.doi, "10.1038/invalid")
        self.assertFalse(fail_result.success)
        self.assertEqual(fail_result.error_message, "Download failed")
        self.assertIsNone(fail_result.file_path)
    
    def test_get_download_statistics(self):
        """Test download statistics generation."""
        # Create test results
        results = [
            DownloadResult("10.1038/1", True, "/path/1.pdf", source="sci-hub"),
            DownloadResult("10.1038/2", True, "/path/2.pdf", source="cached"),
            DownloadResult("10.1038/3", False, error_message="Not found"),
            DownloadResult("10.1038/4", False, error_message="Timeout error")
        ]
        
        stats = self.downloader.get_download_statistics(results)
        
        self.assertEqual(stats["total_attempted"], 4)
        self.assertEqual(stats["successful"], 2)
        self.assertEqual(stats["failed"], 2)
        self.assertEqual(stats["success_rate"], 50.0)
        self.assertIn("sci-hub", stats["sources"])
        self.assertIn("cached", stats["sources"])
        self.assertIn("Not Found", stats["error_types"])
        self.assertIn("Timeout", stats["error_types"])
    
    def test_list_downloaded_files(self):
        """Test listing downloaded files."""
        # Create test PDF files
        test_files = ["paper1.pdf", "paper2.pdf", "document.txt"]
        
        for filename in test_files:
            file_path = Path(self.test_dir) / filename
            file_path.write_text("test content")
        
        files = self.downloader.list_downloaded_files()
        
        # Should only return PDF files
        self.assertEqual(len(files), 2)
        filenames = [f["filename"] for f in files]
        self.assertIn("paper1.pdf", filenames)
        self.assertIn("paper2.pdf", filenames)
        self.assertNotIn("document.txt", filenames)
        
        # Check file info structure
        for file_info in files:
            self.assertIn("filename", file_info)
            self.assertIn("path", file_info)
            self.assertIn("size_mb", file_info)
            self.assertIn("modified", file_info)
    
    def test_batch_download_validation(self):
        """Test batch download input validation."""
        dois = ["10.1038/1", "10.1038/2"]
        titles = ["Title 1"]  # Wrong length
        
        with self.assertRaises(ValueError):
            self.downloader.download_dois_batch(dois, titles)


class TestDOIDownloaderImports(unittest.TestCase):
    """Test import functionality."""
    
    def test_imports(self):
        """Test that all required modules can be imported."""
        try:
            from budapest_hackathlon.tools.doi_downloader import DOIDownloader, DownloadResult
            self.assertTrue(True)  # If we get here, imports worked
        except ImportError:
            # Try alternative import
            try:
                from doi_downloader import DOIDownloader, DownloadResult
                self.assertTrue(True)
            except ImportError as e:
                self.fail(f"Import failed: {e}")


def run_tests():
    """Run all tests."""
    print("Running DOI Downloader Tests")
    print("============================")
    
    # Run tests using unittest.main or TestLoader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDOIDownloader))
    suite.addTests(loader.loadTestsFromTestCase(TestDOIDownloaderImports))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, failure in result.failures:
            print(f"- {test}: {failure}")
    
    if result.errors:
        print("\nErrors:")
        for test, error in result.errors:
            print(f"- {test}: {error}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)