# API Reference

Complete API documentation for all available methods and classes.

## Core Classes

### Scanner

The `Scanner` class handles file discovery and metadata extraction.

```python
from md_mcp.scanner import MarkdownScanner

scanner = MarkdownScanner("./docs")
files = scanner.scan()
```

### Server

The `Server` class implements the MCP protocol.

```python
from md_mcp.server import create_markdown_server

server = create_markdown_server("./docs", "my-docs")
```

## Configuration

See the configuration guide for details on customizing behavior.
