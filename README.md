# PDF Downloader MCP

A robust Model Context Protocol (MCP) server for downloading PDF files with advanced retry logic, error handling, and partial download recovery.

## Features

### ? Core Functionality
- **Single Purpose Tool**: One tool (`download_pdf`) that does PDF downloading exceptionally well
- **Robust Retry Logic**: Exponential backoff with jitter to handle network issues gracefully
- **Partial Download Recovery**: Resume interrupted downloads using HTTP Range requests
- **Comprehensive Error Handling**: Smart classification of errors to determine retry strategies

### ? Advanced Retry Strategies

#### Exponential Backoff
- **First retry**: Wait 5 seconds
- **Second retry**: Wait 10 seconds  
- **Third retry**: Wait 20 seconds
- Prevents overwhelming servers with rapid retry attempts

#### Smart Error Handling
- **Network timeouts**: Retry with longer timeout
- **HTTP 429 (Rate Limited)**: Wait longer, respect rate limits
- **HTTP 503 (Server Unavailable)**: Retry after delay
- **HTTP 404/403**: Don't retry, return error immediately
- **SSL/Certificate errors**: Retry with different SSL settings

#### Partial Download Recovery
- Use HTTP Range requests to resume interrupted downloads
- Check if server supports `Accept-Ranges: bytes`
- Resume from last downloaded byte position
- Fallback to full download if resume fails

#### Download Verification
- Verify file size matches `Content-Length` header
- Basic PDF header validation (starts with `%PDF`)
- Comprehensive PDF structure validation
- Retry if file appears corrupted

#### Fallback Strategies
- Try different User-Agent strings if blocked
- Attempt with/without SSL verification
- Multiple connection strategies for problematic servers

## Installation

### From Source
```bash
git clone https://github.com/baldawsari/pdf-downloader-mcp.git
cd pdf-downloader-mcp
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/baldawsari/pdf-downloader-mcp.git
cd pdf-downloader-mcp
pip install -e ".[dev]"
```

## Usage

### As an MCP Server

1. **Run the server**:
```bash
pdf-downloader-mcp
```

2. **Or run as a Python module**:
```bash
python -m pdf_downloader_mcp
```

### Tool Parameters

The `download_pdf` tool accepts the following parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ? | - | Direct PDF URL |
| `destination_path` | string | ? | - | Local folder path |
| `filename` | string | ? | URL filename | Custom filename |
| `max_retries` | integer | ? | 3 | Number of retry attempts (0-10) |
| `retry_delay` | number | ? | 5.0 | Base delay between retries (0.1-60.0s) |
| `timeout` | number | ? | 30.0 | Request timeout (5.0-300.0s) |

### Example Usage

```json
{
  "tool": "download_pdf",
  "arguments": {
    "url": "https://example.com/document.pdf",
    "destination_path": "/home/user/downloads",
    "filename": "important_document.pdf",
    "max_retries": 5,
    "retry_delay": 10.0,
    "timeout": 60.0
  }
}
```

### Response Format

#### Success Response
```json
{
  "success": true,
  "local_path": "/home/user/downloads/important_document.pdf",
  "file_size": 1234567,
  "attempts_used": 2,
  "max_retries": 5,
  "download_time": 15.3,
  "total_time": 25.8,
  "average_speed": "4.85",
  "resumed": false,
  "bytes_downloaded": 1234567,
  "error_message": null
}
```

#### Error Response
```json
{
  "success": false,
  "local_path": null,
  "file_size": 0,
  "attempts_used": 6,
  "max_retries": 5,
  "download_time": 0,
  "total_time": 45.2,
  "average_speed": "0.00",
  "resumed": false,
  "bytes_downloaded": 0,
  "error_message": "Failed after 6 attempts. Last error: HTTP 404: Not Found"
}
```

## Error Categories

The downloader classifies errors into three categories for optimal retry behavior:

### RETRY Errors
- Network timeouts
- Server errors (5xx)
- Rate limits (429)
- Connection errors
- SSL errors

### NO_RETRY Errors  
- File not found (404)
- Access denied (403)
- Bad request (400)
- Authentication required (401)

### PARTIAL_RETRY Errors
- Incomplete downloads
- Corruption detected
- Validation failures

## Configuration

### MCP Server Configuration

Add to your MCP configuration file:

```json
{
  "mcpServers": {
    "pdf-downloader": {
      "command": "pdf-downloader-mcp",
      "args": []
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PDF_DOWNLOADER_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `PDF_DOWNLOADER_MAX_CONCURRENT` | Maximum concurrent downloads | 5 |

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/ tests/
isort src/ tests/
```

### Type Checking
```bash
mypy src/
```

### Linting
```bash
flake8 src/ tests/
```

## Architecture

```
src/pdf_downloader_mcp/
??? __init__.py          # Package initialization
??? __main__.py          # CLI entry point
??? server.py            # MCP server implementation
??? downloader.py        # Core PDF downloader
??? exceptions.py        # Custom exception classes
??? validators.py        # PDF validation logic
??? utils.py            # Utility functions
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Uses [aiohttp](https://docs.aiohttp.org/) for robust HTTP operations
- Inspired by enterprise-grade download managers

---

**Made with ?? for reliable PDF downloading**
