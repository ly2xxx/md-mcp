"""FastMCP server implementation for markdown files with smart chunking."""

from pathlib import Path
from typing import List, Dict
from fastmcp import FastMCP

from .scanner import MarkdownScanner, MarkdownFile
from .chunking import MarkdownChunker, Chunk


def create_markdown_server(folder_path: str, server_name: str = "markdown-docs") -> FastMCP:
    """Create a FastMCP server that serves markdown files with smart chunking."""
    
    # Initialize scanner and chunker
    scanner = MarkdownScanner(folder_path)
    chunker = MarkdownChunker(max_chunk_size=1000, context_chars=200)
    
    # Create FastMCP instance
    mcp = FastMCP(server_name)
    
    # Caches
    markdown_files: List[MarkdownFile] = []
    file_chunks: Dict[str, List[Chunk]] = {}  # Cache chunks per file
    
    def ensure_scanned():
        """Ensure files are scanned (lazy loading)."""
        nonlocal markdown_files
        if not markdown_files:
            markdown_files = scanner.scan()
            # Pre-load all files for metadata
            for md_file in markdown_files:
                if md_file.content is None:
                    md_file.load()
    
    def get_chunks_for_file(md_file: MarkdownFile) -> List[Chunk]:
        """Get or create chunks for a markdown file."""
        file_key = str(md_file.relative_path)
        
        if file_key not in file_chunks:
            if md_file.content is None:
                md_file.load()
            file_chunks[file_key] = chunker.chunk_markdown(
                md_file.content,
                file_path=str(md_file.relative_path)
            )
        
        return file_chunks[file_key]
    
    @mcp.resource(f"md://{server_name}/{{path}}")
    def read_markdown(path: str) -> str:
        """Read a full markdown file by its relative path.
        
        Args:
            path: Relative path to the markdown file (e.g., "docs/guide.md")
        
        Returns:
            Full markdown content of the file
        
        Note: For large files, consider using search_markdown() or 
        read_file_section() to get specific sections.
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
    def read_file(file_path: str) -> str:
        """Read the full content of a markdown file.
        
        Use this when you need to read an entire file, such as for summarization
        or detailed analysis.
        
        Args:
            file_path: Relative path to the markdown file (e.g., "guide.md" or "decisions/2026-02-01-example.md")
        
        Returns:
            Full markdown content of the file
        
        Note: For large files or searching, prefer search_markdown() or read_file_section()
        """
        ensure_scanned()
        
        # Find the file
        md_file = scanner.get_file_by_relative_path(file_path)
        if not md_file:
            # Try to provide helpful suggestions
            available_files = [str(f.relative_path) for f in markdown_files]
            similar = [f for f in available_files if file_path.lower() in f.lower()]
            
            error_msg = f"File not found: {file_path}\n\n"
            if similar:
                error_msg += f"Did you mean one of these?\n"
                for f in similar[:5]:
                    error_msg += f"  - {f}\n"
            else:
                error_msg += f"Available files ({len(available_files)} total):\n"
                for f in available_files[:10]:
                    error_msg += f"  - {f}\n"
                if len(available_files) > 10:
                    error_msg += f"  ... and {len(available_files) - 10} more\n"
            
            return error_msg
        
        # Load and return content
        if md_file.content is None:
            md_file.load()
        
        # Add metadata header
        file_size = len(md_file.content)
        result = f"# File: {md_file.relative_path}\n"
        result += f"# Size: {file_size} chars ({file_size/1024:.1f} KB)\n"
        if md_file.description:
            result += f"# Description: {md_file.description}\n"
        result += f"\n{md_file.content}"
        
        return result
    
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
                result += f"  {md_file.description[:100]}...\n" if len(md_file.description) > 100 else f"  {md_file.description}\n"
            result += "\n"
        
        return result
    
    @mcp.tool()
    def search_markdown(query: str, max_results: int = 5, strategy: str = "keyword") -> str:
        """Search for markdown content and return SNIPPETS (not full files).
        
        This tool searches across all markdown files and returns relevant
        snippets with context, preventing context bloat.
        
        Args:
            query: Search term to look for
            max_results: Maximum number of snippets to return (default: 5)
            strategy: Search strategy - "keyword" (default), "semantic" (future), "hybrid" (future)
        
        Returns:
            Formatted snippets with file paths and section headers
        """
        ensure_scanned()
        
        # Validate strategy
        valid_strategies = ["keyword", "semantic", "hybrid"]
        if strategy not in valid_strategies:
            return f"Invalid strategy '{strategy}'. Valid options: {', '.join(valid_strategies)}\n\nNote: Only 'keyword' is implemented currently. 'semantic' and 'hybrid' are planned for future releases."
        
        # Check for unimplemented strategies
        if strategy in ["semantic", "hybrid"]:
            return f"Strategy '{strategy}' is not yet implemented. Currently only 'keyword' search is available.\n\nTo enable semantic search in the future:\n  pip install md-mcp[semantic]\n  md-mcp --folder ~/docs --enable-embeddings\n\nFor now, using 'keyword' strategy."
        
        # Collect all chunks from all files
        all_chunks = []
        for md_file in markdown_files:
            chunks = get_chunks_for_file(md_file)
            all_chunks.extend(chunks)
        
        # Search across chunks (keyword strategy)
        snippets = chunker.search_chunks(all_chunks, query, max_results=max_results)
        
        if not snippets:
            return f"No results found for '{query}'"
        
        result = f"Found {len(snippets)} relevant snippet(s) for '{query}':\n\n"
        
        for idx, snippet in enumerate(snippets, 1):
            result += f"**{idx}. {snippet.file_path}**\n"
            result += f"   Section: {snippet.header_path}\n"
            result += f"   Relevance: {snippet.match_score:.2f}\n\n"
            result += f"```\n{snippet.snippet}\n```\n\n"
            result += f"   [Read full file: md://{server_name}/{snippet.file_path}]\n\n"
        
        result += f"\n💡 Tip: Use `read_file_section()` to get specific sections, or access the full file via the resource URI.\n"
        result += f"🔍 Search strategy: {strategy}\n"
        
        return result
    
    @mcp.tool()
    def read_file_section(file_path: str, section_name: str) -> str:
        """Read a specific section from a markdown file by section header.
        
        This is more efficient than loading the entire file when you need
        specific information.
        
        Args:
            file_path: Relative path to the markdown file
            section_name: Section header to look for (e.g., "Installation")
        
        Returns:
            Content of the matching section
        """
        ensure_scanned()
        
        # Find the file
        md_file = scanner.get_file_by_relative_path(file_path)
        if not md_file:
            raise ValueError(f"File not found: {file_path}")
        
        # Get chunks for the file
        chunks = get_chunks_for_file(md_file)
        
        # Find matching section
        section_lower = section_name.lower()
        matching_chunks = [
            chunk for chunk in chunks
            if section_lower in chunk.header_path.lower()
        ]
        
        if not matching_chunks:
            available_sections = list(set(chunk.header_path for chunk in chunks))
            return (
                f"Section '{section_name}' not found in {file_path}\n\n"
                f"Available sections:\n" +
                "\n".join(f"  - {s}" for s in available_sections)
            )
        
        # Return the best matching section
        best_match = matching_chunks[0]
        result = f"**{file_path}** > {best_match.header_path}\n\n"
        result += best_match.content
        
        if len(matching_chunks) > 1:
            result += f"\n\n💡 Note: {len(matching_chunks) - 1} other matching section(s) found."
        
        return result
    
    @mcp.tool()
    def list_file_sections(file_path: str) -> str:
        """List all sections (headers) in a markdown file.
        
        Useful for discovering what sections are available before reading.
        
        Args:
            file_path: Relative path to the markdown file
        
        Returns:
            List of section headers with their hierarchy
        """
        ensure_scanned()
        
        # Find the file
        md_file = scanner.get_file_by_relative_path(file_path)
        if not md_file:
            raise ValueError(f"File not found: {file_path}")
        
        # Get chunks for the file
        chunks = get_chunks_for_file(md_file)
        
        # Extract unique section headers
        sections = []
        seen = set()
        for chunk in chunks:
            if chunk.header_path not in seen:
                sections.append({
                    "path": chunk.header_path,
                    "size": f"{len(chunk)} chars"
                })
                seen.add(chunk.header_path)
        
        result = f"**Sections in {file_path}:**\n\n"
        for section in sections:
            result += f"- {section['path']} ({section['size']})\n"
        
        result += f"\n💡 Use `read_file_section('{file_path}', 'section_name')` to read a specific section.\n"
        
        return result
    
    @mcp.tool()
    def get_markdown_stats() -> str:
        """Get statistics about the markdown collection.
        
        Returns:
            Summary statistics (file count, total size, chunk stats)
        """
        ensure_scanned()
        
        total_files = len(markdown_files)
        total_chars = sum(len(f.content or "") for f in markdown_files)
        total_kb = total_chars / 1024
        
        # Calculate chunk stats
        total_chunks = 0
        for md_file in markdown_files:
            chunks = get_chunks_for_file(md_file)
            total_chunks += len(chunks)
        
        avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0
        
        # Group by subdirectory
        dirs = {}
        for md_file in markdown_files:
            parent = str(md_file.relative_path.parent)
            if parent == ".":
                parent = "(root)"
            dirs[parent] = dirs.get(parent, 0) + 1
        
        result = f"**Markdown Collection Stats**\n\n"
        result += f"📄 Files: {total_files}\n"
        result += f"📦 Total size: {total_kb:.1f} KB\n"
        result += f"📊 Average file size: {total_kb/total_files:.1f} KB\n"
        result += f"🧩 Total chunks: {total_chunks}\n"
        result += f"📏 Average chunk size: {avg_chunk_size:.0f} chars\n\n"
        
        if len(dirs) > 1:
            result += "**Files by directory:**\n"
            for dir_name, count in sorted(dirs.items()):
                result += f"  - {dir_name}: {count} file(s)\n"
        
        return result
    
    return mcp


def main(folder_path: str, server_name: str = "markdown-docs"):
    """Main entry point for running the server."""
    mcp = create_markdown_server(folder_path, server_name)
    mcp.run()
