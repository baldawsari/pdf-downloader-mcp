#!/usr/bin/env python3
"""
Example usage of the PDF Downloader MCP Server.

This script demonstrates how to use the PDF downloader both as a standalone
library and as an MCP tool.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from pdf_downloader_mcp import PDFDownloader, PDFDownloaderServer


async def example_standalone_usage():
    """Example of using PDFDownloader directly."""
    print("? Example 1: Using PDFDownloader directly")
    
    # Create a temporary directory for downloads
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = PDFDownloader()
        
        try:
            # Example PDF URL (replace with a real PDF URL for testing)
            test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
            
            print(f"? Downloading from: {test_url}")
            print(f"? Saving to: {temp_dir}")
            
            result = await downloader.download_pdf(
                url=test_url,
                destination_path=temp_dir,
                filename="example_download.pdf",
                max_retries=3,
                retry_delay=2.0,
                timeout=30.0
            )
            
            print("? Download Result:")
            print(json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"? Error during download: {e}")
        
        finally:
            await downloader._close_session()


async def example_mcp_tool_usage():
    """Example of using the MCP server tool interface."""
    print("\n? Example 2: Using MCP Server Tool Interface")
    
    # Create server instance
    server = PDFDownloaderServer()
    
    # Example tool call arguments
    arguments = {
        "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "destination_path": tempfile.mkdtemp(),
        "filename": "mcp_example.pdf",
        "max_retries": 2,
        "retry_delay": 1.0,
        "timeout": 20.0
    }
    
    try:
        print(f"??  Calling download_pdf tool with arguments:")
        print(json.dumps(arguments, indent=2))
        
        # This simulates how an MCP client would call the tool
        result = await server.server._call_tool("download_pdf", arguments)
        
        print("? MCP Tool Result:")
        for content in result:
            if hasattr(content, 'text'):
                print(content.text)
            else:
                print(f"Content: {content}")
                
    except Exception as e:
        print(f"? Error during MCP tool call: {e}")


def example_configuration():
    """Example of different configuration options."""
    print("\n? Example 3: Configuration Options")
    
    print("? Available configuration options for download_pdf:")
    
    config_examples = {
        "minimal": {
            "url": "https://example.com/document.pdf",
            "destination_path": "/home/user/downloads"
        },
        "basic": {
            "url": "https://example.com/document.pdf", 
            "destination_path": "/home/user/downloads",
            "filename": "my_document.pdf"
        },
        "robust": {
            "url": "https://example.com/document.pdf",
            "destination_path": "/home/user/downloads", 
            "filename": "important_document.pdf",
            "max_retries": 5,
            "retry_delay": 10.0,
            "timeout": 60.0
        },
        "quick": {
            "url": "https://example.com/document.pdf",
            "destination_path": "/home/user/downloads",
            "max_retries": 1,
            "retry_delay": 1.0,
            "timeout": 10.0
        }
    }
    
    for name, config in config_examples.items():
        print(f"\n? {name.title()} Configuration:")
        print(json.dumps(config, indent=2))


async def main():
    """Run all examples."""
    print("? PDF Downloader MCP Server - Usage Examples")
    print("=" * 50)
    
    # Example 1: Direct usage
    await example_standalone_usage()
    
    # Example 2: MCP tool usage  
    await example_mcp_tool_usage()
    
    # Example 3: Configuration options
    example_configuration()
    
    print("\n" + "=" * 50)
    print("? Examples completed!")
    print("\n? To run the MCP server:")
    print("   pdf-downloader-mcp")
    print("\n? To run as a Python module:")
    print("   python -m pdf_downloader_mcp")
    print("\n? For more information, see the README.md file")


if __name__ == "__main__":
    asyncio.run(main())
