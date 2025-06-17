@echo off
REM install.bat - Windows installation script for PDF Downloader MCP

echo ? Installing PDF Downloader MCP Server...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ? Python 3 is required but not installed.
    echo Please install Python 3.8+ from https://python.org and try again.
    pause
    exit /b 1
)

REM Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo ? pip is required but not installed.
    echo Please install pip and try again.
    pause
    exit /b 1
)

REM Install the package
echo ? Installing from GitHub...
pip install git+https://github.com/baldawsari/pdf-downloader-mcp.git

REM Test installation
echo ? Testing installation...
pdf-downloader-mcp --version >nul 2>&1
if errorlevel 1 (
    echo ??  Command not found. You may need to add Python Scripts to your PATH.
    echo Try running: python -m pdf_downloader_mcp --version
) else (
    echo ? Installation successful!
    pdf-downloader-mcp --version
)

echo.
echo ? Next steps:
echo 1. Add the following to your Claude Desktop configuration:
echo.
echo {
echo   "mcpServers": {
echo     "pdf-downloader": {
echo       "command": "pdf-downloader-mcp",
echo       "args": []
echo     }
echo   }
echo }
echo.
echo 2. Restart Claude Desktop
echo 3. Ask Claude to download a PDF!
echo.
echo ? Config file location:
echo   %%APPDATA%%\Claude\claude_desktop_config.json
echo.
pause
