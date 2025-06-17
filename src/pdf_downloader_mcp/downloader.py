"""
PDF Downloader with advanced retry logic and error handling.

This module provides the core downloading functionality with:
- Exponential backoff retry strategy
- Partial download recovery using HTTP Range requests
- Comprehensive error classification and handling
- Download verification and validation
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, unquote
import aiohttp
import aiofiles
from aiohttp import ClientSession, ClientTimeout, ClientResponseError

from .exceptions import (
    DownloadError,
    RetryableError,
    NonRetryableError,
    ValidationError
)
from .validators import PDFValidator
from .utils import (
    sanitize_filename,
    format_file_size,
    calculate_download_speed
)

logger = logging.getLogger(__name__)

class PDFDownloader:
    """
    Robust PDF downloader with advanced retry logic.
    
    Features:
    - Exponential backoff with jitter
    - Partial download recovery
    - Multiple User-Agent fallbacks
    - SSL/TLS error handling
    - Rate limiting respect
    - Download verification
    """
    
    # Common User-Agent strings for fallback
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "curl/8.0.1"  # Fallback for services that prefer curl
    ]
    
    def __init__(self):
        self.validator = PDFValidator()
        self._session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _create_session(self, user_agent_index: int = 0) -> ClientSession:
        """Create an aiohttp session with appropriate configuration."""
        if self._session and not self._session.closed:
            await self._session.close()
        
        timeout = ClientTimeout(total=300, connect=30)  # 5 min total, 30s connect
        
        headers = {
            "User-Agent": self.USER_AGENTS[user_agent_index % len(self.USER_AGENTS)],
            "Accept": "application/pdf,application/octet-stream,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
            enable_cleanup_closed=True
        )
        
        self._session = ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector,
            trust_env=True
        )
        
        return self._session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _calculate_backoff_delay(self, attempt: int, base_delay: float) -> float:
        """
        Calculate exponential backoff delay with jitter.
        
        Args:
            attempt: Current attempt number (0-based)
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds with exponential backoff and jitter
        """
        import random
        
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = base_delay * (2 ** attempt)
        
        # Add jitter (?25% of delay) to prevent thundering herd
        jitter = delay * 0.25 * (2 * random.random() - 1)
        
        # Cap maximum delay at 5 minutes
        return min(delay + jitter, 300.0)
    
    def _classify_error(self, error: Exception) -> Tuple[bool, str]:
        """
        Classify errors to determine if retry should be attempted.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Tuple of (should_retry, error_description)
        """
        if isinstance(error, ClientResponseError):
            status = error.status
            
            # Permanent errors - don't retry
            if status in [400, 401, 403, 404, 410, 451]:
                return False, f"HTTP {status}: {error.message}"
            
            # Rate limiting - retry with longer delay
            if status == 429:
                return True, f"Rate limited (HTTP 429)"
            
            # Server errors - retry
            if status >= 500:
                return True, f"Server error (HTTP {status})"
            
            # Other client errors - don't retry
            if 400 <= status < 500:
                return False, f"Client error (HTTP {status})"
                
            return True, f"HTTP {status}: {error.message}"
        
        elif isinstance(error, asyncio.TimeoutError):
            return True, "Request timeout"
        
        elif isinstance(error, aiohttp.ClientConnectorError):
            return True, f"Connection error: {str(error)}"
        
        elif isinstance(error, aiohttp.ClientSSLError):
            return True, f"SSL error: {str(error)}"
        
        elif isinstance(error, aiohttp.ClientError):
            return True, f"Client error: {str(error)}"
        
        else:
            # Unknown errors - try once more
            return True, f"Unknown error: {str(error)}"
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL, ensuring it's a valid PDF name."""
        parsed = urlparse(url)
        filename = unquote(parsed.path.split('/')[-1])
        
        if not filename or filename == '/':
            filename = "document.pdf"
        
        # Ensure .pdf extension
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        return sanitize_filename(filename)
    
    async def _check_resume_capability(self, url: str) -> Tuple[bool, int]:
        """
        Check if the server supports partial content (resume capability).
        
        Returns:
            Tuple of (supports_resume, content_length)
        """
        try:
            async with self._session.head(url) as response:
                supports_resume = response.headers.get('Accept-Ranges') == 'bytes'
                content_length = int(response.headers.get('Content-Length', 0))
                return supports_resume, content_length
        except Exception as e:
            logger.debug(f"Failed to check resume capability: {e}")
            return False, 0
    
    async def _download_with_resume(
        self,
        url: str,
        file_path: Path,
        timeout: float
    ) -> Dict[str, Any]:
        """
        Download file with resume capability if partially downloaded.
        
        Args:
            url: URL to download from
            file_path: Local file path
            timeout: Request timeout
            
        Returns:
            Dictionary with download statistics
        """
        start_time = time.time()
        
        # Check if file exists and get its size
        existing_size = 0
        if file_path.exists():
            existing_size = file_path.stat().st_size
            logger.info(f"Found partial file: {existing_size} bytes")
        
        # Check if server supports resume
        supports_resume, total_size = await self._check_resume_capability(url)
        
        # If file is complete, return success
        if existing_size > 0 and total_size > 0 and existing_size >= total_size:
            logger.info("File already complete")
            return {
                "success": True,
                "bytes_downloaded": 0,
                "total_size": existing_size,
                "resumed": True,
                "download_time": time.time() - start_time
            }
        
        # Set up headers for resume if supported
        headers = {}
        if supports_resume and existing_size > 0:
            headers['Range'] = f'bytes={existing_size}-'
            logger.info(f"Resuming download from byte {existing_size}")
        
        bytes_downloaded = 0
        
        try:
            async with self._session.get(
                url,
                headers=headers,
                timeout=ClientTimeout(total=timeout)
            ) as response:
                response.raise_for_status()
                
                # Open file in appropriate mode
                mode = 'ab' if existing_size > 0 else 'wb'
                
                async with aiofiles.open(file_path, mode) as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        bytes_downloaded += len(chunk)
                
                total_time = time.time() - start_time
                
                return {
                    "success": True,
                    "bytes_downloaded": bytes_downloaded,
                    "total_size": existing_size + bytes_downloaded,
                    "resumed": existing_size > 0,
                    "download_time": total_time
                }
                
        except Exception as e:
            # If resume failed, try full download
            if existing_size > 0:
                logger.warning(f"Resume failed, attempting full download: {e}")
                if file_path.exists():
                    file_path.unlink()  # Delete partial file
                return await self._download_with_resume(url, file_path, timeout)
            raise
    
    async def download_pdf(
        self,
        url: str,
        destination_path: str,
        filename: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Download a PDF file with robust retry logic.
        
        Args:
            url: Direct URL to the PDF file
            destination_path: Local directory path
            filename: Custom filename (optional)
            max_retries: Maximum retry attempts
            retry_delay: Base delay between retries
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with download result and statistics
        """
        overall_start_time = time.time()
        
        # Validate inputs
        if not url or not destination_path:
            raise ValidationError("URL and destination_path are required")
        
        # Prepare file paths
        dest_dir = Path(destination_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            filename = self._extract_filename_from_url(url)
        
        file_path = dest_dir / sanitize_filename(filename)
        
        # Initialize session
        await self._create_session()
        
        last_error = None
        user_agent_index = 0
        
        try:
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Download attempt {attempt + 1}/{max_retries + 1}: {url}")
                    
                    # Download with resume capability
                    result = await self._download_with_resume(url, file_path, timeout)
                    
                    # Validate downloaded file
                    if file_path.exists():
                        validation_result = await self.validator.validate_pdf(file_path)
                        if not validation_result["is_valid"]:
                            raise ValidationError(f"Invalid PDF: {validation_result['error']}")
                    
                    # Success! Calculate final statistics
                    file_size = file_path.stat().st_size
                    total_time = time.time() - overall_start_time
                    avg_speed = calculate_download_speed(file_size, result["download_time"])
                    
                    return {
                        "success": True,
                        "local_path": str(file_path.absolute()),
                        "file_size": file_size,
                        "attempts_used": attempt + 1,
                        "max_retries": max_retries,
                        "download_time": result["download_time"],
                        "total_time": total_time,
                        "average_speed": f"{avg_speed:.2f}",
                        "resumed": result.get("resumed", False),
                        "bytes_downloaded": result["bytes_downloaded"],
                        "error_message": None
                    }
                    
                except Exception as error:
                    last_error = error
                    should_retry, error_desc = self._classify_error(error)
                    
                    logger.warning(f"Attempt {attempt + 1} failed: {error_desc}")
                    
                    # Clean up partial file on certain errors
                    if isinstance(error, (ValidationError, ClientResponseError)) and file_path.exists():
                        file_path.unlink()
                    
                    # If this was the last attempt or error is non-retryable
                    if attempt >= max_retries or not should_retry:
                        break
                    
                    # Special handling for rate limiting
                    if isinstance(error, ClientResponseError) and error.status == 429:
                        # Extract retry-after header if available
                        retry_after = error.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                delay = self._calculate_backoff_delay(attempt, retry_delay)
                        else:
                            delay = self._calculate_backoff_delay(attempt, retry_delay * 2)
                    else:
                        delay = self._calculate_backoff_delay(attempt, retry_delay)
                    
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                    
                    # Try different User-Agent on connection/SSL errors
                    if isinstance(error, (aiohttp.ClientConnectorError, aiohttp.ClientSSLError)):
                        user_agent_index += 1
                        await self._create_session(user_agent_index)
            
            # All attempts failed
            total_time = time.time() - overall_start_time
            error_msg = f"Failed after {max_retries + 1} attempts. Last error: {str(last_error)}"
            
            return {
                "success": False,
                "local_path": None,
                "file_size": 0,
                "attempts_used": max_retries + 1,
                "max_retries": max_retries,
                "download_time": 0,
                "total_time": total_time,
                "average_speed": "0.00",
                "resumed": False,
                "bytes_downloaded": 0,
                "error_message": error_msg
            }
            
        finally:
            await self._close_session()
