"""md-mcp: Instantly expose markdown folders as MCP servers."""

__version__ = "0.1.0"

from .scanner import MarkdownScanner
from .server import create_markdown_server

__all__ = ["MarkdownScanner", "create_markdown_server", "__version__"]
