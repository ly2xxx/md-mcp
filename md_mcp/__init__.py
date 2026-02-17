"""md-mcp: Instantly expose markdown folders as MCP servers."""

__version__ = "0.3.0"

from .scanner import MarkdownScanner
from .chunking import MarkdownChunker

# Server imports are optional (require fastmcp)
try:
    from .server import create_markdown_server
    __all__ = ["MarkdownScanner", "MarkdownChunker", "create_markdown_server", "__version__"]
except ImportError:
    __all__ = ["MarkdownScanner", "MarkdownChunker", "__version__"]
