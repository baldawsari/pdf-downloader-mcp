"""
PDF Downloader MCP Package

A robust Model Context Protocol server for downloading PDF files with advanced retry logic.
"""

__version__ = "1.0.0"
__author__ = "baldawsari"
__email__ = "55813250+baldawsari@users.noreply.github.com"

from .downloader import PDFDownloader
from .server import PDFDownloaderServer
from .exceptions import (
    DownloadError,
    RetryableError,
    NonRetryableError,
    ValidationError
)

__all__ = [
    "PDFDownloader",
    "PDFDownloaderServer", 
    "DownloadError",
    "RetryableError",
    "NonRetryableError",
    "ValidationError"
]
