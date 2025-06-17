"""
Basic integration test for the PDF Downloader MCP server.

This test verifies that the server can be initialized and the download_pdf tool
is properly configured.
"""

import pytest
from pdf_downloader_mcp import PDFDownloaderServer, PDFDownloader


class TestPDFDownloaderServer:
    """Test the main MCP server functionality."""
    
    def test_server_initialization(self):
        """Test that the server can be initialized without errors."""
        server = PDFDownloaderServer()
        assert server is not None
        assert server.server is not None
        assert server.downloader is not None
        assert isinstance(server.downloader, PDFDownloader)
    
    def test_server_name(self):
        """Test that the server has the correct name."""
        server = PDFDownloaderServer()
        assert server.server.name == "pdf-downloader-mcp"


class TestPDFDownloader:
    """Test the core PDF downloader functionality."""
    
    def test_downloader_initialization(self):
        """Test that the downloader can be initialized without errors."""
        downloader = PDFDownloader()
        assert downloader is not None
        assert downloader.validator is not None
        assert downloader._session is None  # Should be None until created
    
    def test_user_agents_available(self):
        """Test that User-Agent strings are configured."""
        downloader = PDFDownloader()
        assert len(downloader.USER_AGENTS) > 0
        assert all(isinstance(ua, str) for ua in downloader.USER_AGENTS)
    
    def test_extract_filename_from_url(self):
        """Test filename extraction from URLs."""
        downloader = PDFDownloader()
        
        # Test normal PDF URL
        filename = downloader._extract_filename_from_url("https://example.com/document.pdf")
        assert filename == "document.pdf"
        
        # Test URL without extension
        filename = downloader._extract_filename_from_url("https://example.com/document")
        assert filename == "document.pdf"
        
        # Test URL with query parameters
        filename = downloader._extract_filename_from_url("https://example.com/report.pdf?version=1")
        assert filename == "report.pdf"
        
        # Test URL with no filename
        filename = downloader._extract_filename_from_url("https://example.com/")
        assert filename == "document.pdf"
    
    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation."""
        downloader = PDFDownloader()
        
        # Test first retry (attempt 0)
        delay = downloader._calculate_backoff_delay(0, 5.0)
        assert 3.75 <= delay <= 6.25  # 5.0 ? 25% jitter
        
        # Test second retry (attempt 1) 
        delay = downloader._calculate_backoff_delay(1, 5.0)
        assert 7.5 <= delay <= 12.5  # 10.0 ? 25% jitter
        
        # Test third retry (attempt 2)
        delay = downloader._calculate_backoff_delay(2, 5.0)
        assert 15.0 <= delay <= 25.0  # 20.0 ? 25% jitter
        
        # Test maximum delay cap (5 minutes)
        delay = downloader._calculate_backoff_delay(10, 5.0)
        assert delay <= 300.0


class TestErrorClassification:
    """Test error classification logic."""
    
    def test_error_classification_setup(self):
        """Test that error classification method exists and is callable."""
        downloader = PDFDownloader()
        assert hasattr(downloader, '_classify_error')
        assert callable(downloader._classify_error)


if __name__ == "__main__":
    pytest.main([__file__])
