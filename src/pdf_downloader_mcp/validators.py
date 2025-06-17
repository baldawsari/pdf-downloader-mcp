"""
PDF validation utilities.

This module provides functionality to validate downloaded PDF files
to ensure they are complete and correctly formatted.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PDFValidator:
    """
    Validates PDF files to ensure they are complete and properly formatted.
    
    Performs multiple validation checks:
    - File header validation (PDF magic bytes)
    - File size validation (not empty)
    - Basic structure validation
    - EOF marker validation
    """
    
    # PDF file signatures
    PDF_SIGNATURES = [
        b'%PDF-1.0',
        b'%PDF-1.1',
        b'%PDF-1.2',
        b'%PDF-1.3',
        b'%PDF-1.4',
        b'%PDF-1.5',
        b'%PDF-1.6',
        b'%PDF-1.7',
        b'%PDF-2.0'
    ]
    
    # Minimum reasonable PDF size (in bytes)
    MIN_PDF_SIZE = 100
    
    # Maximum size to read for header/footer validation (in bytes)
    VALIDATION_CHUNK_SIZE = 1024
    
    async def validate_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate a PDF file asynchronously.
        
        Args:
            file_path: Path to the PDF file to validate
            
        Returns:
            Dictionary with validation results:
            {
                "is_valid": bool,
                "file_size": int,
                "pdf_version": str,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        result = {
            "is_valid": False,
            "file_size": 0,
            "pdf_version": None,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check if file exists
            if not file_path.exists():
                result["errors"].append("File does not exist")
                return result
            
            # Check file size
            file_size = file_path.stat().st_size
            result["file_size"] = file_size
            
            if file_size == 0:
                result["errors"].append("File is empty")
                return result
            
            if file_size < self.MIN_PDF_SIZE:
                result["errors"].append(f"File too small ({file_size} bytes), likely corrupted")
                return result
            
            # Read file header and footer for validation
            header_data = await self._read_file_chunk(file_path, 0, self.VALIDATION_CHUNK_SIZE)
            footer_data = await self._read_file_chunk(
                file_path, 
                max(0, file_size - self.VALIDATION_CHUNK_SIZE), 
                self.VALIDATION_CHUNK_SIZE
            )
            
            # Validate PDF header
            header_valid, pdf_version = self._validate_pdf_header(header_data)
            if not header_valid:
                result["errors"].append("Invalid PDF header - file may be corrupted or not a PDF")
                return result
            
            result["pdf_version"] = pdf_version
            
            # Validate PDF footer/structure
            footer_valid, footer_warnings = self._validate_pdf_footer(footer_data)
            if not footer_valid:
                result["errors"].append("Invalid PDF structure - file may be incomplete or corrupted")
                return result
            
            result["warnings"].extend(footer_warnings)
            
            # Additional structural validation
            structure_valid, structure_warnings = self._validate_pdf_structure(header_data, footer_data)
            if not structure_valid:
                result["errors"].append("PDF structure validation failed")
                return result
            
            result["warnings"].extend(structure_warnings)
            
            # If we got here, the PDF is valid
            result["is_valid"] = True
            
            logger.debug(f"PDF validation successful: {file_path} ({file_size:,} bytes, version {pdf_version})")
            
        except Exception as e:
            logger.error(f"PDF validation error for {file_path}: {e}")
            result["errors"].append(f"Validation error: {str(e)}")
        
        return result
    
    async def _read_file_chunk(self, file_path: Path, offset: int, size: int) -> bytes:
        """Read a chunk of data from a file asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            
            def read_chunk():
                with open(file_path, 'rb') as f:
                    f.seek(offset)
                    return f.read(size)
            
            return await loop.run_in_executor(None, read_chunk)
        
        except Exception as e:
            logger.error(f"Error reading file chunk from {file_path}: {e}")
            return b''
    
    def _validate_pdf_header(self, header_data: bytes) -> tuple[bool, str]:
        """
        Validate PDF file header.
        
        Returns:
            Tuple of (is_valid, pdf_version)
        """
        if len(header_data) < 8:
            return False, None
        
        # Check for PDF signature
        for signature in self.PDF_SIGNATURES:
            if header_data.startswith(signature):
                version = signature.decode('ascii').split('-')[1]
                return True, version
        
        # Check for PDF signature anywhere in the first 1024 bytes
        # (some PDFs have extra data before the PDF header)
        for signature in self.PDF_SIGNATURES:
            if signature in header_data:
                version = signature.decode('ascii').split('-')[1]
                logger.warning("PDF signature found but not at file start")
                return True, version
        
        return False, None
    
    def _validate_pdf_footer(self, footer_data: bytes) -> tuple[bool, list]:
        """
        Validate PDF file footer/trailer.
        
        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        
        if len(footer_data) < 10:
            return False, ["Footer data too short"]
        
        # Look for EOF marker
        footer_str = footer_data.decode('latin-1', errors='ignore')
        
        # Check for proper PDF EOF
        if '%%EOF' in footer_str:
            return True, warnings
        
        # Check for common PDF trailer elements
        if any(marker in footer_str for marker in ['trailer', 'xref', 'startxref']):
            warnings.append("PDF appears to have proper structure but missing %%EOF marker")
            return True, warnings
        
        return False, ["No valid PDF trailer found"]
    
    def _validate_pdf_structure(self, header_data: bytes, footer_data: bytes) -> tuple[bool, list]:
        """
        Perform additional structural validation.
        
        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        
        try:
            header_str = header_data.decode('latin-1', errors='ignore')
            footer_str = footer_data.decode('latin-1', errors='ignore')
            
            # Check for common PDF objects in header
            if not any(obj in header_str for obj in ['obj', '<<', '>>']):
                warnings.append("PDF header doesn't contain expected object markers")
            
            # Check for cross-reference table indicators
            if 'xref' not in footer_str and 'xref' not in header_str:
                warnings.append("No cross-reference table found - PDF may be damaged")
            
            # Check for catalog/root object references
            if '/Root' not in header_str and '/Root' not in footer_str:
                warnings.append("No root object reference found")
            
            return True, warnings
            
        except Exception as e:
            logger.error(f"Error during structural validation: {e}")
            return False, [f"Structural validation failed: {str(e)}"]
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable validation summary.
        
        Args:
            validation_result: Result from validate_pdf()
            
        Returns:
            Formatted summary string
        """
        if validation_result["is_valid"]:
            summary = f"? Valid PDF file"
            if validation_result["pdf_version"]:
                summary += f" (version {validation_result['pdf_version']})"
            summary += f"\n? Size: {validation_result['file_size']:,} bytes"
            
            if validation_result["warnings"]:
                summary += f"\n??  Warnings: {len(validation_result['warnings'])}"
                for warning in validation_result["warnings"]:
                    summary += f"\n   ? {warning}"
        else:
            summary = "? Invalid PDF file"
            if validation_result["errors"]:
                summary += f"\n? Errors: {len(validation_result['errors'])}"
                for error in validation_result["errors"]:
                    summary += f"\n   ? {error}"
        
        return summary
