<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@2e2a28d -->
## Summary
Adds a new MCP tool, `list_file_sizes`, to the Markdown server created in `md_mcp/server.py`. It lets MCP clients list every Markdown file already exposed by the server together with that file’s size in bytes, sorted by relative path. Empty or missing folders return a clear message instead of an error.

## Behaviour
1. Given the MCP server is running, when an MCP client discovers available tools, then `list_file_sizes` is available as a callable tool with no required arguments.
2. Given the configured folder contains one or more Markdown files that the existing scanner exposes, when `list_file_sizes` is called, then the result lists every such file by its relative path.
3. Given a listed Markdown file has an on-disk size of N bytes, when `list_file_sizes` is called, then that file’s entry reports the size as `N bytes`.
4. Given multiple Markdown files are exposed, when `list_file_sizes` is called, then entries are sorted by relative path ascending, using `/` as the path separator.
5. Given the configured folder exists but contains no Markdown files exposed by the existing scanner, when `list_file_sizes` is called, then it returns a clear empty-result message and does not raise an error.
6. Given the configured folder is missing or inaccessible, when `list_file_sizes` is called, then it returns a clear missing-folder message and does not raise an unhandled error.
7. Given a file was exposed by the scanner but cannot be read or stat’ed at call time, when `list_file_sizes` is called, then the tool still lists the remaining files and reports that file’s size as unavailable rather than failing the whole call.
8. Given files are hidden or excluded by the existing scan behavior, when `list_file_sizes` is called, then those files do not appear in the result.
9. Given the existing test suite, when it is run after this change, then all previously passing tests still pass.

## Interfaces
`md_mcp/server.py`, inside `create_markdown_server(folder_path: str, server_name: str = "markdown-docs") -> FastMCP`:

```python
@mcp.tool()
def list_file_sizes() -> str:
    """List available markdown files and their sizes in bytes.

    Returns:
        A string listing every exposed markdown file, sorted by relative
        path ascending, with its size in bytes. If no files are available,
        returns a clear empty or missing-folder message.
    """
```

No parameters are added. The return type is `str`, matching the existing MCP tools in `md_mcp/server.py`.

No changes are made to `MarkdownScanner`, `MarkdownFile`, `MarkdownChunker`, `md_mcp/config.py`, or existing tool signatures.

## Out of scope
- Sorting beyond relative path ascending, and any filtering, paging, or grouping.
- Content previews, word counts, line counts, modification times, or other file metadata.
- Cleanup actions, deletion, or recommendations about which files to remove.
- Changes to file scanning, file watching, or folder configuration behavior.
- Web UI changes for viewing Markdown file sizes.
- Changes to existing MCP tools or resources such as `list_files`, `read_file`, `search_markdown`, and `rescan_folder`.
- Human-readable unit conversion beyond raw bytes.

## Open questions
- Should the tool cover all configured folders or only the active server’s folder? Assumption: it covers the same Markdown files the active server already exposes via its `folder_path`; multiple folders are separate server instances.
- What unit should sizes use? Assumption: raw bytes, always available and consistent; human-readable units are not required.
- Should results be sorted? Assumption: yes, by relative path ascending.
- Should hidden or excluded Markdown files appear? Assumption: only files already included by the existing scan behavior.
- What should happen when the folder is missing? Assumption: return a clear missing-folder message rather than an error.
- What should happen if a scanned file disappears before its size is read? Assumption: report that file’s size as unavailable and continue listing the rest.
