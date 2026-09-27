<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@aac8739 -->
## Summary
Adds a new MCP tool, `list_file_sizes()`, to the FastMCP server created by `create_markdown_server` in `md_mcp/server.py`, so MCP clients can see how large each discovered Markdown file is without leaving the session. Each entry reports the file's relative path and its size in bytes, using the same recursive Markdown discovery already used by `list_files`, `read_file`, and `search_markdown`. No existing tool behaviour changes.

## Behaviour
1. Given a configured folder containing one or more Markdown files, when an MCP client calls `list_file_sizes()`, then the response contains exactly one entry per discovered Markdown file, and each entry contains that file's relative path and its size as a decimal integer of bytes.
2. Given Markdown files nested in subdirectories of the configured folder, when `list_file_sizes()` is called, then those nested files appear as entries, matching the discovery rules already used by the existing tools (`.md` per `MARKDOWN_EXTENSIONS`, recursive, same root folder).
3. Given a configured folder containing no Markdown files, when `list_file_sizes()` is called, then it returns the message `No markdown files found in {folder_path}.` and does not raise.
4. Given files in the configured folder that are not Markdown (extension not in `MARKDOWN_EXTENSIONS`), when `list_file_sizes()` is called, then no entry is returned for those files.
5. Given a Markdown file that was added, modified, or deleted since the last scan, when `list_file_sizes()` is called, then the folder is rescanned before reporting, and the byte sizes returned reflect the files currently on disk.
6. Given a Markdown file whose content contains multi-byte characters or exceeds `MD_MAX_READ_CHARS`, when `list_file_sizes()` is called, then the reported size equals the on-disk byte count (`os.stat().st_size`), not `len(content)` of any decoded, truncated, or in-memory representation.
7. Given a Markdown file that is discovered by the scan but cannot be read when the size is measured (for example it was deleted or made unreadable in between), when `list_file_sizes()` is called, then that file's entry is omitted, the remaining entries are still returned, and the call does not raise.
8. Given multiple Markdown files, when `list_file_sizes()` is called, then entry order is the order produced by the existing scan (`MarkdownScanner.scan()`), with no additional sorting, grouping, or filtering.
9. Given the existing test suite, when it is run against this change, then all tests that passed before still pass.

## Interfaces

**`md_mcp/scanner.py`** — add a read-only byte-size accessor to `MarkdownFile`:

```python
class MarkdownFile:
    # ... existing fields and methods unchanged ...

    @property
    def size_bytes(self) -> int:
        """Size of this file on disk in bytes (os.stat().st_size)."""
```

It is derived from the same on-disk path that `MarkdownFile.load()` already reads, and raises `OSError` when the file cannot be stat-ed. No change to `MarkdownScanner` or `MARKDOWN_EXTENSIONS`.

**`md_mcp/server.py`** — add one tool inside `create_markdown_server`, alongside the existing `@mcp.tool()` functions (place it directly after `list_files`):

```python
@mcp.tool()
def list_file_sizes() -> str:
    """List each discovered markdown file with its size in bytes.

    Returns:
        One line per markdown file, each with the file's relative path
        (forward slashes) and its size in bytes, or a message when the
        folder contains no markdown files.
    """
```

- Signature: no parameters, returns `str` (same convention as `list_files`, `rescan_folder`, `search_markdown`, `read_file`).
- Uses `ensure_scanned()` and the module-level `markdown_files` list, and normalizes paths the same way existing tools do (`str(md_file.relative_path).replace('\\', '/')`).
- Response starts with a header in the style of `list_files` (`Found {n} markdown file(s) in {folder_path}:`) followed by one entry line per file containing the relative path and the byte count labelled `bytes`; the empty case returns exactly the string in Behaviour criterion 3.
- No new middleware, resource, CLI flag, or config value; existing OpenTelemetry middleware covers the new tool automatically.

## Out of scope
- Reading, previewing, summarizing, or returning Markdown file contents.
- Word counts, metadata extraction, chunk counts, or any statistics other than byte size.
- Search, filtering, sorting, grouping, pagination/limits, or size-threshold alerts.
- Changing the output of any existing tool (`list_files`, `read_file`, `rescan_folder`, `search_markdown`) or adding a new MCP resource.
- Changes to the Web UI, CLI, chunking, semantic search, telemetry, packaging, or deployment setup (Docker, Kubernetes, Helm).
- New caching behaviour beyond the existing scan cache and watchdog invalidation.

## Open questions
- Tool name: the intent does not name it. Assumption: `list_file_sizes()`, matching the `list_files` naming style.
- Result shape: the intent says "a list of entries" but not whether it is structured data. Assumption: a human-readable `str`, consistent with every existing tool in `md_mcp/server.py`.
- Unreadable or vanished files: the intent does not say. Assumption: skip the affected entry and still return the rest (Behaviour criterion 7) rather than failing the whole call.
- Total size or header count: not requested. Assumption: the response follows `list_files` header style with a file count, and does not add a total-bytes figure.
- Unit: confirmed as bytes by the intent; reported as a plain integer with a `bytes` label, no human-readable formatting (KB/MB).
