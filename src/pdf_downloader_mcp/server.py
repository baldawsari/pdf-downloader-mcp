#!/usr/bin/env python3
"""
PDF Downloader MCP Server

A robust Model Context Protocol server for downloading PDF files with advanced
retry logic, error handling, and partial download recovery.
"""

import asyncio
import logging
from typing import Any, Sequence

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

from .downloader import PDFDownloader
from .exceptions import DownloadError
from .utils import setup_logging

# Configure logging
logger = logging.getLogger(__name__)

class PDFDownloaderServer:
    """MCP Server for PDF downloading with robust error handling."""
    
    def __init__(self):
        self.server = Server("pdf-downloader-mcp")
        self.downloader = PDFDownloader()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="download_pdf",
                    description="Download a PDF file from a URL to a local directory with robust retry logic",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Direct URL to the PDF file",
                                "format": "uri"
                            },
                            "destination_path": {
                                "type": "string",
                                "description": "Local directory path where the PDF should be saved"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Custom filename for the downloaded PDF (optional, defaults to URL filename)",
                                "default": None
                            },
                            "max_retries": {
                                "type": "integer",
                                "description": "Maximum number of retry attempts (default: 3)",
                                "minimum": 0,
                                "maximum": 10,
                                "default": 3
                            },
                            "retry_delay": {
                                "type": "number",
                                "description": "Base delay in seconds between retries (default: 5.0)",
                                "minimum": 0.1,
                                "maximum": 60.0,
                                "default": 5.0
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Request timeout in seconds (default: 30.0)",
                                "minimum": 5.0,
                                "maximum": 300.0,
                                "default": 30.0
                            }
                        },
                        "required": ["url", "destination_path"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls."""
            if name != "download_pdf":
                raise ValueError(f"Unknown tool: {name}")
            
            try:
                # Extract arguments with defaults
                url = arguments["url"]
                destination_path = arguments["destination_path"]
                filename = arguments.get("filename")
                max_retries = arguments.get("max_retries", 3)
                retry_delay = arguments.get("retry_delay", 5.0)
                timeout = arguments.get("timeout", 30.0)
                
                # Validate inputs
                if not url or not destination_path:
                    raise ValueError("URL and destination_path are required")
                
                # Perform the download
                result = await self.downloader.download_pdf(
                    url=url,
                    destination_path=destination_path,
                    filename=filename,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                    timeout=timeout
                )
                
                # Format response
                response_text = self._format_download_response(result)
                
                return [TextContent(type="text", text=response_text)]
                
            except DownloadError as e:
                error_msg = f"Download failed: {e}"
                logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]
            
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]
    
    def _format_download_response(self, result: dict[str, Any]) -> str:
        """Format the download result into a human-readable response."""
        if result["success"]:
            return f"""? PDF Download Successful

? Local Path: {result['local_path']}
? File Size: {result['file_size']:,} bytes ({result['file_size'] / 1024 / 1024:.2f} MB)
? Attempts Used: {result['attempts_used']}/{result.get('max_retries', 'unknown')}
??  Download Time: {result['download_time']:.2f} seconds
? Average Speed: {result.get('average_speed', 'unknown')} MB/s"""
        else:
            return f"""? PDF Download Failed

? Error: {result['error_message']}
? Attempts Used: {result['attempts_used']}/{result.get('max_retries', 'unknown')}
??  Total Time: {result.get('total_time', 'unknown')} seconds

? Suggestions:
- Check if the URL is accessible
- Verify the destination path exists and is writable
- Try again with increased retry count or delay"""

async def main():
    """Main entry point for the MCP server."""
    setup_logging()
    
    # Create and run the server
    server_instance = PDFDownloaderServer()
    
    # Run the server with stdio transport
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pdf-downloader-mcp",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
