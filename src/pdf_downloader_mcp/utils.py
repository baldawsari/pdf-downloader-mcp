"""
Utility functions for the PDF Downloader MCP.

This module provides various helper functions for file handling,
logging setup, and data formatting.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Union


def setup_logging(level: Union[str, int] = logging.INFO) -> None:
    """
    Set up logging configuration for the MCP server.
    
    Args:
        level: Logging level (default: INFO)
    """
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stderr)  # Use stderr to avoid interfering with MCP stdio
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('aiofiles').setLevel(logging.WARNING)
    
    # Set our logger to debug in development
    logger = logging.getLogger('pdf_downloader_mcp')
    logger.setLevel(level)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to be safe for filesystem use.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "document.pdf"
    
    # Remove or replace invalid characters
    # Invalid characters for most filesystems: < > : " | ? * \ /
    invalid_chars = r'[<>:"|?*\\\/]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Handle reserved names on Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(sanitized).stem.upper()
    if name_without_ext in reserved_names:
        sanitized = f"_{sanitized}"
    
    # Truncate if too long, but preserve extension
    if len(sanitized) > max_length:
        path_obj = Path(sanitized)
        stem = path_obj.stem
        suffix = path_obj.suffix
        
        # Calculate how much we can keep of the stem
        available_length = max_length - len(suffix)
        if available_length > 0:
            sanitized = stem[:available_length] + suffix
        else:
            # If even the extension is too long, just truncate everything
            sanitized = sanitized[:max_length]
    
    # Ensure we have a .pdf extension
    if not sanitized.lower().endswith('.pdf'):
        sanitized += '.pdf'
    
    return sanitized


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def calculate_download_speed(bytes_downloaded: int, time_seconds: float) -> float:
    """
    Calculate download speed in MB/s.
    
    Args:
        bytes_downloaded: Number of bytes downloaded
        time_seconds: Time taken in seconds
        
    Returns:
        Download speed in MB/s
    """
    if time_seconds <= 0:
        return 0.0
    
    mb_downloaded = bytes_downloaded / (1024 * 1024)
    return mb_downloaded / time_seconds


def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted and likely to be a PDF.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL appears valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL format check
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))


def validate_destination_path(path: str) -> tuple[bool, str]:
    """
    Validate if a destination path is valid and accessible.
    
    Args:
        path: Destination path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Destination path is required"
    
    try:
        path_obj = Path(path)
        
        # Check if path is absolute or can be resolved
        if not path_obj.is_absolute():
            path_obj = path_obj.resolve()
        
        # Create directory if it doesn't exist
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Check if directory is writable
        if not path_obj.exists():
            return False, f"Could not create directory: {path_obj}"
        
        if not path_obj.is_dir():
            return False, f"Path is not a directory: {path_obj}"
        
        # Test write permissions by creating a temporary file
        test_file = path_obj / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            return False, f"Directory is not writable: {e}"
        
        return True, ""
        
    except Exception as e:
        return False, f"Invalid destination path: {e}"


def get_url_filename(url: str) -> str:
    """
    Extract filename from URL path.
    
    Args:
        url: URL to extract filename from
        
    Returns:
        Extracted filename or default name
    """
    try:
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        if path and path != '/':
            filename = Path(path).name
            if filename and '.' in filename:
                return filename
        
        # Fallback to a default name
        return "document.pdf"
        
    except Exception:
        return "document.pdf"


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize a path to a Path object with proper resolution.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized Path object
    """
    if isinstance(path, str):
        path = Path(path)
    
    # Resolve to absolute path
    return path.expanduser().resolve()


def is_pdf_url(url: str) -> bool:
    """
    Check if URL likely points to a PDF file.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to point to a PDF
    """
    if not url:
        return False
    
    url_lower = url.lower()
    
    # Check file extension
    if url_lower.endswith('.pdf'):
        return True
    
    # Check for PDF in query parameters
    if 'pdf' in url_lower:
        return True
    
    # Check for common PDF-serving patterns
    pdf_patterns = [
        '/pdf/',
        'download=pdf',
        'format=pdf',
        'type=pdf',
        '.pdf?',
        'application/pdf'
    ]
    
    return any(pattern in url_lower for pattern in pdf_patterns)


class ProgressTracker:
    """Simple progress tracking for downloads."""
    
    def __init__(self, total_size: int = 0):
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = None
    
    def start(self):
        """Start tracking progress."""
        import time
        self.start_time = time.time()
    
    def update(self, bytes_downloaded: int):
        """Update progress with new bytes downloaded."""
        self.downloaded += bytes_downloaded
    
    def get_progress_percent(self) -> float:
        """Get download progress as percentage."""
        if self.total_size <= 0:
            return 0.0
        return min(100.0, (self.downloaded / self.total_size) * 100)
    
    def get_speed(self) -> float:
        """Get current download speed in MB/s."""
        if not self.start_time:
            return 0.0
        
        import time
        elapsed = time.time() - self.start_time
        return calculate_download_speed(self.downloaded, elapsed)
    
    def get_eta(self) -> float:
        """Get estimated time remaining in seconds."""
        if self.total_size <= 0 or self.downloaded <= 0:
            return 0.0
        
        speed = self.get_speed()
        if speed <= 0:
            return 0.0
        
        remaining_mb = (self.total_size - self.downloaded) / (1024 * 1024)
        return remaining_mb / speed
