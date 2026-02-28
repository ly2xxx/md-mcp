"""FastMCP server implementation for markdown files with semantic chunking."""

from pathlib import Path
from typing import List, Dict, Optional
from fastmcp import FastMCP

from .scanner import MarkdownScanner, MarkdownFile
from .chunking import MarkdownChunker, Chunk
# Optional import for semantic functionality
try:
    from .semantic import SemanticIndex, SEMANTIC_AVAILABLE
except Exception:
    SEMANTIC_AVAILABLE = False
    SemanticIndex = None  # type: ignore


def create_markdown_server(folder_path: str, server_name: str = "markdown-docs") -> FastMCP:
    """Create a FastMCP server that serves markdown files with chunking and semantic indexing."""

    scanner = MarkdownScanner(folder_path)
    chunker = MarkdownChunker(max_chunk_size=1000, context_chars=200)
    mcp = FastMCP(server_name)

    # Caches
    markdown_files: List[MarkdownFile] = []
    file_chunks: Dict[str, List[Chunk]] = {}
    _all_chunks: List[Chunk] = []

    # Semantic index (lazy-initialised)
    semantic_index: Optional[SemanticIndex] = None
    _index_built = False

    def ensure_scanned():
        nonlocal markdown_files
        if not markdown_files:
            markdown_files = scanner.scan()
            for md_file in markdown_files:
                if md_file.content is None:
                    md_file.load()

    def get_chunks_for_file(md_file: MarkdownFile) -> List[Chunk]:
        file_key = str(md_file.relative_path)
        if file_key not in file_chunks:
            if md_file.content is None:
                md_file.load()
            file_chunks[file_key] = chunker.chunk_markdown(
                md_file.content,
                file_path=str(md_file.relative_path)
            )
        return file_chunks[file_key]

    def get_all_chunks() -> List[Chunk]:
        nonlocal _all_chunks
        ensure_scanned()
        if not _all_chunks:
            for md_file in markdown_files:
                _all_chunks.extend(get_chunks_for_file(md_file))
        return _all_chunks

    def get_semantic_index() -> Optional[SemanticIndex]:
        """Return a built SemanticIndex, or None if unavailable/not built."""
        nonlocal semantic_index, _index_built
        if not SEMANTIC_AVAILABLE:
            return None
        if semantic_index is None:
            cache_dir = str(Path(folder_path))
            semantic_index = SemanticIndex(cache_dir=cache_dir)
        if not _index_built:
            chunks = get_all_chunks()
            if chunks:
                n = semantic_index.build_index(chunks)
                _index_built = True
        return semantic_index

    @mcp.resource(f"md://{server_name}/{{path}}")
    def read_markdown(path: str) -> str:
        """Read a full markdown file by its relative path."""
        ensure_scanned()
        md_file = scanner.get_file_by_relative_path(path)
        if not md_file:
            raise ValueError(f"File not found: {path}")
        if md_file.content is None:
            md_file.load()
        return md_file.content

    @mcp.tool()
    def search_markdown(query: str, max_results: int = 5, strategy: str = "keyword") -> str:
        """Search for markdown content and return SNIPPETS (not full files).

        Args:
            query: Search term or natural language question
            max_results: Maximum number of snippets to return (default: 5)
            strategy: "keyword" (default, fast), "semantic" (embedding-based), or "hybrid" (best quality, combines both)

        Returns:
            Formatted snippets with file paths, section headers and relevance scores
        """
        ensure_scanned()

        valid = ["keyword", "semantic", "hybrid"]
        if strategy not in valid:
            return f"Invalid strategy '{strategy}'. Choose from: {', '.join(valid)}"

        if strategy in ("semantic", "hybrid") and not SEMANTIC_AVAILABLE:
            return (
                "Strategy '{strategy}' requires sentence-transformers.\n"
                "Install: pip install sentence-transformers"
            )

        chunks = get_all_chunks()

        if strategy == "keyword":
            snippets = chunker.search_chunks(chunks, query, max_results=max_results)

        elif strategy == "semantic":
            idx = get_semantic_index()
            if idx is None:
                return "Semantic index unavailable."
            sem_results = idx.search(query, chunks, top_k=max_results)
            from .chunking import SearchSnippet
            snippets = [
                SearchSnippet(
                    file_path=chunk.file_path,
                    header_path=chunk.header_path,
                    snippet=chunker.extract_snippet(chunk, query),
                    full_chunk=chunk.content,
                    match_score=score,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                )
                for chunk, score in sem_results
            ]

        else:  # hybrid
            idx = get_semantic_index()
            snippets = chunker.search_hybrid(
                chunks, query,
                semantic_index=idx,
                max_results=max_results,
                vector_weight=0.7,
                text_weight=0.3,
            )

        if not snippets:
            return f"No results found for '{query}' (strategy: {strategy})"

        result = f"Found {len(snippets)} snippet(s) for '{query}' [{strategy}]:\n\n"
        for idx_n, snippet in enumerate(snippets, 1):
            result += f"**{idx_n}. {snippet.file_path}**\n"
            result += f"   Section: {snippet.header_path}\n"
            result += f"   Score: {snippet.match_score:.3f}\n\n"
            result += f"```\n{snippet.snippet}\n```\n\n"
            result += f"   [Full file: md://{server_name}/{snippet.file_path}]\n\n"

        result += "💡 Tip: Use `read_file_section()` to read a specific section.\n"
        return result

    return mcp


def main(folder_path: str, server_name: str = "markdown-docs"):
    """Main entry point for running the server."""
    mcp = create_markdown_server(folder_path, server_name)
    mcp.run()