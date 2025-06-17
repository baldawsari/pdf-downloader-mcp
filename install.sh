#!/bin/bash
# install.sh - Quick installation script for PDF Downloader MCP

set -e

echo "? Installing PDF Downloader MCP Server..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "? Python 3 is required but not installed."
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "? pip is required but not installed."
    echo "Please install pip and try again."
    exit 1
fi

# Install the package
echo "? Installing from GitHub..."
pip install git+https://github.com/baldawsari/pdf-downloader-mcp.git

# Test installation
echo "? Testing installation..."
if command -v pdf-downloader-mcp &> /dev/null; then
    echo "? Installation successful!"
    pdf-downloader-mcp --version
else
    echo "??  Command not found. You may need to add Python scripts to your PATH."
    echo "Try running: python -m pdf_downloader_mcp --version"
fi

echo ""
echo "? Next steps:"
echo "1. Add the following to your Claude Desktop configuration:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "pdf-downloader": {'
echo '      "command": "pdf-downloader-mcp",'
echo '      "args": []'
echo '    }'
echo '  }'
echo '}'
echo ""
echo "2. Restart Claude Desktop"
echo "3. Ask Claude to download a PDF!"
echo ""
echo "? Config file locations:"
echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo "  Linux: ~/.config/Claude/claude_desktop_config.json"
