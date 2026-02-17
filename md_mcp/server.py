"""FastMCP server implementation for markdown files."""

from pathlib import Path
from typing import List
from fastmcp import FastMCP

from .scanner import MarkdownScanner, MarkdownFile


def create_markdown_server(folder_path: str, server_name: str = "markdown-docs") -> FastMCP:
    """Create a FastMCP server that serves markdown files."""
    
    # Initialize scanner
    scanner = MarkdownScanner(folder_path)
    
    # Create FastMCP instance
    mcp = FastMCP(server_name)
    
    # Scan files on startup
    markdown_files: List[MarkdownFile] = []
    
    def ensure_scanned():
        """Ensure files are scanned (lazy loading)."""
        nonlocal markdown_files
        if not markdown_files:
            markdown_files = scanner.scan()
            # Pre-load all files for metadata
            for md_file in markdown_files:
                if md_file.content is None:
                    md_file.load()
    
    @mcp.resource(f"md://{server_name}/{{path}}")
    def read_markdown(path: str) -> str:
        """Read a markdown file by its relative path.
        
        Args:
            path: Relative path to the markdown file (e.g., "docs/guide.md")
        
        Returns:
            Full markdown content of the file
        """
        ensure_scanned()
        
        # Find the file
        md_file = scanner.get_file_by_relative_path(path)
        if not md_file:
            raise ValueError(f"File not found: {path}")
        
        # Load and return content
        if md_file.content is None:
            md_file.load()
        
        return md_file.content
    
    @mcp.tool()
    def list_markdown_files() -> str:
        """List all available markdown files in the folder.
        
        Returns:
            Formatted list of all markdown files with their paths and descriptions
        """
        ensure_scanned()
        
        if not markdown_files:
            return "No markdown files found."
        
        result = f"Found {len(markdown_files)} markdown file(s):\n\n"
        for md_file in markdown_files:
            result += f"**{md_file.relative_path}**\n"
            if md_file.description:
                result += f"  {md_file.description}\n"
            result += "\n"
        
        return result
    
    @mcp.tool()
    def search_markdown(query: str) -> str:
        """Search for markdown files by content or filename.
        
        Args:
            query: Search term to look for in filenames and content
        
        Returns:
            List of matching files with snippets
        """
        ensure_scanned()
        
        results = scanner.search(query)
        
        if not results:
            return f"No files found matching '{query}'"
        
        result = f"Found {len(results)} file(s) matching '{query}':\n\n"
        for md_file in results[:10]:  # Limit to 10 results
            result += f"**{md_file.relative_path}**\n"
            if md_file.description:
                result += f"  {md_file.description[:150]}...\n"
            result += "\n"
        
        if len(results) > 10:
            result += f"... and {len(results) - 10} more results\n"
        
        return result
    
    @mcp.tool()
    def get_markdown_stats() -> str:
        """Get statistics about the markdown collection.
        
        Returns:
            Summary statistics (file count, total size, etc.)
        """
        ensure_scanned()
        
        total_files = len(markdown_files)
        total_chars = sum(len(f.content or "") for f in markdown_files)
        total_kb = total_chars / 1024
        
        # Group by subdirectory
        dirs = {}
        for md_file in markdown_files:
            parent = str(md_file.relative_path.parent)
            if parent == ".":
                parent = "(root)"
            dirs[parent] = dirs.get(parent, 0) + 1
        
        result = f"**Markdown Collection Stats**\n\n"
        result += f"- Total files: {total_files}\n"
        result += f"- Total size: {total_kb:.1f} KB\n"
        result += f"- Average file size: {total_kb/total_files:.1f} KB\n\n"
        
        if len(dirs) > 1:
            result += "**Files by directory:**\n"
            for dir_name, count in sorted(dirs.items()):
                result += f"- {dir_name}: {count} files\n"
        
        return result
    
    return mcp


def main(folder_path: str, server_name: str = "markdown-docs"):
    """Main entry point for running the server."""
    mcp = create_markdown_server(folder_path, server_name)
    mcp.run()
