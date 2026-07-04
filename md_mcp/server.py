"""FastMCP server implementation for markdown files with semantic chunking and auto-reload."""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
import time
import sys
from fastmcp import FastMCP

from .scanner import MarkdownScanner, MarkdownFile
from .chunking import MarkdownChunker, Chunk
from . import telemetry

# Set up logging
logger = logging.getLogger(__name__)

# Optional import for semantic functionality
try:
    from .semantic import SemanticIndex, SEMANTIC_AVAILABLE
except Exception:
    SEMANTIC_AVAILABLE = False
    SemanticIndex = None  # type: ignore

# Optional import for file watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCH_AVAILABLE = True
except ImportError:
    WATCH_AVAILABLE = False
    Observer = None  # type: ignore
    FileSystemEventHandler = None  # type: ignore


def _semantic_cache_dir(folder_path: str) -> str:
    """Directory for the semantic embeddings cache — OUTSIDE the notes folder.

    Writing the cache into the served folder forced users to drop the ``:ro``
    mount for semantic search, giving up the "never writes to your notes"
    guarantee. Override with ``MD_CACHE_DIR``; defaults to ``~/.cache/md-mcp``.
    A digest of the folder path keeps caches of different served folders apart.
    """
    import hashlib

    base = os.environ.get("MD_CACHE_DIR") or str(Path.home() / ".cache" / "md-mcp")
    digest = hashlib.sha256(str(Path(folder_path).resolve()).encode()).hexdigest()[:16]
    return str(Path(base) / digest)


class MarkdownFileWatcher(FileSystemEventHandler):
    """Watches for changes to markdown files and invalidates cache."""
    
    def __init__(self, invalidate_callback):
        super().__init__()
        self.invalidate_callback = invalidate_callback
        self.last_invalidate = 0
        self.debounce_seconds = 1.0  # Debounce rapid changes
    
    def _should_invalidate(self, event_path: str) -> bool:
        """Check if we should invalidate cache for this event."""
        # Only invalidate for markdown files
        if not event_path.endswith('.md'):
            return False
        
        # Debounce rapid changes
        current_time = time.time()
        if current_time - self.last_invalidate < self.debounce_seconds:
            return False
        
        self.last_invalidate = current_time
        return True
    
    def on_created(self, event):
        """Called when a file or directory is created."""
        if event.is_directory:
            return
        if self._should_invalidate(event.src_path):
            logger.info(f"File watcher: New file detected: {event.src_path}")
            sys.stderr.write(f"[md-mcp watchdog] New file: {event.src_path}\n")
            sys.stderr.flush()
            self.invalidate_callback()
    
    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if event.is_directory:
            return
        if self._should_invalidate(event.src_path):
            logger.info(f"File watcher: File modified: {event.src_path}")
            sys.stderr.write(f"[md-mcp watchdog] Modified: {event.src_path}\n")
            sys.stderr.flush()
            self.invalidate_callback()
    
    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        if event.is_directory:
            return
        if self._should_invalidate(event.src_path):
            logger.info(f"File watcher: File deleted: {event.src_path}")
            sys.stderr.write(f"[md-mcp watchdog] Deleted: {event.src_path}\n")
            sys.stderr.flush()
            self.invalidate_callback()


def create_markdown_server(folder_path: str, server_name: str = "markdown-docs") -> FastMCP:
    """Create a FastMCP server that serves markdown files with chunking and semantic indexing."""

    scanner = MarkdownScanner(folder_path)
    chunker = MarkdownChunker(max_chunk_size=1000, context_chars=200)
    mcp = FastMCP(server_name)

    # Cap for read_file responses; huge files blow out the model's context.
    MAX_READ_CHARS = int(os.environ.get("MD_MAX_READ_CHARS", "60000"))

    # Optional OpenTelemetry tracing (no-op unless the `observability` extra is
    # installed and a collector endpoint is reachable). Instruments every MCP
    # request via middleware, so all tools below are covered automatically.
    if telemetry.init_telemetry():
        otel_middleware = telemetry.create_tracing_middleware()
        if otel_middleware is not None:
            mcp.add_middleware(otel_middleware)

    # Caches
    markdown_files: List[MarkdownFile] = []
    file_chunks: Dict[str, List[Chunk]] = {}
    _all_chunks: List[Chunk] = []

    # Semantic index (lazy-initialised)
    semantic_index: Optional[SemanticIndex] = None
    _index_built = False

    # File watcher observer
    observer: Optional[Observer] = None

    def invalidate_cache():
        """Invalidate all caches to force rescan on next access."""
        nonlocal markdown_files, file_chunks, _all_chunks, _index_built
        logger.info("Cache invalidated - will rescan on next access")
        sys.stderr.write(f"[md-mcp watchdog] Cache invalidated\n")
        sys.stderr.flush()
        markdown_files = []
        file_chunks = {}
        _all_chunks = []
        _index_built = False

    def ensure_scanned():
        nonlocal markdown_files
        if not markdown_files:
            markdown_files = scanner.scan()
            logger.info(f"Scanned {len(markdown_files)} markdown files from {folder_path}")
            sys.stderr.write(f"[md-mcp] Scanned {len(markdown_files)} files from {folder_path}\n")
            sys.stderr.flush()
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
            semantic_index = SemanticIndex(cache_dir=_semantic_cache_dir(folder_path))
        if not _index_built:
            chunks = get_all_chunks()
            if chunks:
                n = semantic_index.build_index(chunks)
                _index_built = True
        return semantic_index

    # Start file watcher if available
    if WATCH_AVAILABLE:
        try:
            observer = Observer()
            event_handler = MarkdownFileWatcher(invalidate_cache)
            observer.schedule(event_handler, folder_path, recursive=True)
            observer.start()
            logger.info(f"File watcher started - monitoring {folder_path}")
            sys.stderr.write(f"[md-mcp watchdog] ✓ File watcher STARTED - monitoring {folder_path}\n")
            sys.stderr.flush()
        except Exception as e:
            logger.warning(f"Could not start file watcher: {e}")
            sys.stderr.write(f"[md-mcp watchdog] ✗ Failed to start: {e}\n")
            sys.stderr.flush()
            observer = None
    else:
        logger.info("File watcher not available - watchdog not installed")
        sys.stderr.write(f"[md-mcp watchdog] ✗ Not available - watchdog not installed\n")
        sys.stderr.flush()

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
    def read_file(path: str, section: str = "") -> str:
        """Read a markdown file by its relative path (as shown by list_files /
        search_markdown), either in full or just one section.

        Args:
            path: Relative path of the file, e.g. "notes/project.md"
            section: Optional header name (or part of one) to return only the
                matching section(s) instead of the whole file, e.g. "Setup"

        Returns:
            The file content (or matching sections), or an error listing
            similar paths if the file is not found.
        """
        ensure_scanned()
        md_file = scanner.get_file_by_relative_path(path)
        if not md_file:
            # Help the model recover: suggest close matches (handles typos).
            import difflib
            all_paths = [str(f.relative_path).replace('\\', '/') for f in markdown_files]
            suggestions = difflib.get_close_matches(path, all_paths, n=5, cutoff=0.4)
            hint = f"\nDid you mean: {', '.join(suggestions)}" if suggestions else ""
            return f"File not found: {path}. Use list_files() to see available paths.{hint}"

        if md_file.content is None:
            md_file.load()

        if section:
            chunks = get_chunks_for_file(md_file)
            wanted = section.lower()
            matches = [c for c in chunks if wanted in c.header_path.lower()]
            if not matches:
                sections = sorted({c.header_path for c in chunks})
                return (
                    f"No section matching '{section}' in {path}.\n"
                    f"Available sections:\n" + "\n".join(f"- {s}" for s in sections)
                )
            header = f"# {path} — sections matching '{section}'\n\n"
            return header + "\n\n---\n\n".join(c.content for c in matches)

        content = md_file.content or ""
        if len(content) > MAX_READ_CHARS:
            return (
                content[:MAX_READ_CHARS]
                + f"\n\n[... truncated at {MAX_READ_CHARS} characters — "
                f"use the 'section' argument to read a specific part]"
            )
        return content

    @mcp.tool()
    def rescan_folder() -> str:
        """Manually rescan the folder for new, modified, or deleted markdown files.
        
        Use this tool if:
        - You've added new markdown files and they're not showing up in searches
        - You've modified files and want to force a refresh
        - File watcher is not available or not working
        
        The file watcher (when available) handles this automatically, but this tool
        provides manual control when needed.
        
        Returns:
            Summary of files found after rescan
        """
        invalidate_cache()
        ensure_scanned()
        
        return (
            f"✅ Folder rescanned successfully!\n\n"
            f"Found {len(markdown_files)} markdown files in {folder_path}\n\n"
            f"File watcher status: {'Active' if observer and observer.is_alive() else 'Not available'}"
        )

    @mcp.tool()
    def list_files() -> str:
        """List all available markdown files.
        
        Returns:
            A list of all markdown files available in the server.
        """
        ensure_scanned()
        
        if not markdown_files:
            return f"No markdown files found in {folder_path}."
        
        result = f"Found {len(markdown_files)} markdown file(s):\n\n"
        for md_file in markdown_files:
            path_str = str(md_file.relative_path).replace('\\', '/')
            result += f"- **{path_str}**\n"
            if md_file.description:
                result += f"  Description: {md_file.description}\n"
            result += f"  [md://{server_name}/{path_str}]\n\n"
            
        return result

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

        result += "💡 Tip: Use `read_file(path)` for the whole file, or `read_file(path, section=\"...\")` for one section.\n"
        result += f"\n📁 Tip: If files are missing, use `rescan_folder()` to refresh.\n"
        return result

    # Store observer reference for cleanup if needed
    mcp._observer = observer

    return mcp


def main(folder_path: str, server_name: str = "markdown-docs"):
    """Main entry point for running the server."""
    mcp = create_markdown_server(folder_path, server_name)
    try:
        mcp.run()
    finally:
        # Cleanup file watcher on exit
        if hasattr(mcp, '_observer') and mcp._observer:
            mcp._observer.stop()
            mcp._observer.join()
            logger.info("File watcher stopped")
            sys.stderr.write("[md-mcp watchdog] File watcher stopped\n")
            sys.stderr.flush()
