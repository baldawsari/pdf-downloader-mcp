"""
Custom exceptions for the PDF Downloader MCP.

This module defines specific exception types to help classify and handle
different types of errors that can occur during PDF downloading.
"""


class DownloadError(Exception):
    """Base exception for all download-related errors."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class RetryableError(DownloadError):
    """
    Exception for errors that should trigger a retry attempt.
    
    These include:
    - Network timeouts
    - Server errors (5xx)
    - Rate limiting (429)
    - Connection issues
    - SSL/TLS errors
    """
    pass


class NonRetryableError(DownloadError):
    """
    Exception for errors that should NOT trigger a retry attempt.
    
    These include:
    - File not found (404)
    - Access denied (403)
    - Bad request (400)
    - Authentication required (401)
    - Invalid URLs
    """
    pass


class ValidationError(DownloadError):
    """
    Exception for file validation errors.
    
    These include:
    - Invalid PDF format
    - Corrupted files
    - Empty files
    - File size mismatches
    """
    pass


class ConfigurationError(DownloadError):
    """
    Exception for configuration-related errors.
    
    These include:
    - Invalid destination paths
    - Permission errors
    - Disk space issues
    - Invalid parameters
    """
    pass


class RateLimitError(RetryableError):
    """
    Specific exception for rate limiting scenarios.
    
    This allows for special handling of rate limits, such as
    respecting Retry-After headers or using longer delays.
    """
    
    def __init__(self, message: str, retry_after: float = None, original_error: Exception = None):
        super().__init__(message, original_error)
        self.retry_after = retry_after


class PartialDownloadError(RetryableError):
    """
    Exception for partial download failures.
    
    This is used when a download starts successfully but fails
    partway through, and can potentially be resumed.
    """
    
    def __init__(self, message: str, bytes_downloaded: int = 0, total_size: int = 0, original_error: Exception = None):
        super().__init__(message, original_error)
        self.bytes_downloaded = bytes_downloaded
        self.total_size = total_size
