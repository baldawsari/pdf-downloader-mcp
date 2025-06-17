#!/usr/bin/env python3
"""
Command-line interface for PDF Downloader MCP Server.

This module provides the main entry point for running the PDF Downloader MCP server
from the command line or as a Python module.
"""

import asyncio
import sys
from typing import Optional

import click

from .server import PDFDownloaderServer


@click.command()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set the logging level",
)
@click.option(
    "--host",
    default="localhost", 
    help="Host to bind the server to (for future HTTP transport)"
)
@click.option(
    "--port", 
    default=8000,
    type=int,
    help="Port to bind the server to (for future HTTP transport)"
)
@click.version_option(version="1.0.0", prog_name="pdf-downloader-mcp")
def main(log_level: str, host: str, port: int) -> None:
    """
    PDF Downloader MCP Server
    
    A robust Model Context Protocol server for downloading PDF files with 
    advanced retry logic, error handling, and partial download recovery.
    
    The server provides a single tool 'download_pdf' that handles PDF downloads
    with enterprise-grade reliability features.
    """
    
    # Import here to avoid circular imports
    from .utils import setup_logging
    
    # Configure logging
    setup_logging(level=log_level.upper())
    
    try:
        # Run the MCP server
        asyncio.run(_run_server())
    except KeyboardInterrupt:
        click.echo("\n? Server shutdown requested by user", err=True)
        sys.exit(0)
    except Exception as e:
        click.echo(f"? Server failed to start: {e}", err=True)
        sys.exit(1)


async def _run_server() -> None:
    """Run the MCP server with stdio transport."""
    from mcp.server.stdio import stdio_server
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions
    
    # Create server instance
    server_instance = PDFDownloaderServer()
    
    click.echo("? Starting PDF Downloader MCP Server...", err=True)
    click.echo("? Using stdio transport", err=True)
    click.echo("? Ready to handle PDF download requests", err=True)
    
    # Run with stdio transport
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


def cli() -> None:
    """Entry point for the CLI when installed as a package."""
    main()


if __name__ == "__main__":
    main()
