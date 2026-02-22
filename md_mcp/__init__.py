"""md-mcp: Instantly expose markdown folders as MCP servers."""

__version__ = "0.4.0"

from .scanner import MarkdownScanner
from .chunking import MarkdownChunker

# SemanticIndex and SEMANTIC_AVAILABLE are imported lazily to avoid
# crashing the package import on machines where sentence-transformers
# or its torch dependency has DLL/library issues.
# Import explicitly: from md_mcp.semantic import SemanticIndex, SEMANTIC_AVAILABLE

# Server imports are optional (require fastmcp)
try:
    from .server import create_markdown_server
    __all__ = [
        "MarkdownScanner", "MarkdownChunker",
        "create_markdown_server", "__version__",
    ]
except ImportError:
    __all__ = [
        "MarkdownScanner", "MarkdownChunker",
        "__version__",
    ]
