<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@cee1b80 -->
## Summary

Adds a new MCP tool, `list_file_sizes`, to the server created by `create_markdown_server` in `md_mcp/server.py`, so a user can ask their AI client for the size of each markdown file in the served folder. Sizes come from the file paths the existing `MarkdownScanner` already discovers, and are reported as raw bytes per file. No existing tool, flag, or UI behaviour changes.

## Behaviour

1. Given a running md-mcp server, when an MCP client lists the available tools, then a tool named `list_file_sizes` is exposed whose description states that it lists the sizes of the markdown files in the served folder.
2. Given a served folder containing markdown files, when `list_file_sizes()` is called with no arguments, then it returns exactly one entry per markdown file the scanner discovers in that folder, each entry carrying that file's relative path and its size in bytes.
3. Given a served folder with markdown files inside subfolders, when `list_file_sizes()` is called, then the markdown files in those subfolders are included, and files whose extension is not `.md`, `.markdown`, or `.mdx` are not.
4. Given any entry returned by `list_file_sizes()`, when its reported size is compared with the byte size the filesystem reports for the same file, then the two values are equal.
5. Given an unchanged served folder, when `list_file_sizes()` is called twice, then both results are identical, with entries ordered by ascending relative path.
6. Given a served folder that contains no markdown files, when `list_file_sizes()` is called, then it returns an empty result and reports no error.
7. Given a file the scanner discovered that no longer exists or whose size cannot be read when the tool runs, when `list_file_sizes()` is called, then that file is omitted from the result and the call still succeeds with the remaining entries.
8. Given the existing test suite, when it is run after this change, then it passes unchanged.

## Interfaces

### `md_mcp/scanner.py`

Add a method to `MarkdownFile`, next to `to_uri` / `to_resource_dict`:

```python
def get_size_bytes(self) -> int:
    """Return this file's size in bytes, as reported by the filesystem."""
```

### `md_mcp/server.py`

Extend the existing typing import to include `Any`:

```python
from typing import Any, Dict, List, Optional
```

Add one tool inside `create_markdown_server`, alongside the other `@mcp.tool()` functions (`read_file`, `rescan_folder`, `list_files`, `search_markdown`):

```python
@mcp.tool()
def list_file_sizes() -> List[Dict[str, Any]]:
    """List every markdown file in the served folder together with its size in bytes.

    Returns:
        One entry per markdown file discovered by the scanner, each a dict with:
        - "path": relative path of the file, e.g. "notes/project.md"
        - "size_bytes": size of the file in bytes, as reported by the filesystem
        Entries are ordered by ascending "path"; the list is empty when the
        folder contains no markdown files.
    """
```

Return contract: `list[dict]` where each dict has exactly the string key `"path"` (forward-slash relative path, the same form `read_file` accepts) and the integer key `"size_bytes"`. No other signatures change.

## Out of scope

- Sorting, ranking, filtering by size, size thresholds, or flagging "large" files.
- Human-readable unit formatting (KB/MB) or rounding — sizes are raw bytes.
- Non-markdown files, directory sizes, or disk-usage reporting.
- Persisting, caching, or exposing size history or size changes over time beyond the existing rescan/file-watcher behaviour.
- Changes to the web UI, CLI flags, or telemetry.
- Adding parameters to the new tool (for example `pattern` or `limit`) or adding size information to the output of existing tools such as `list_files`, `read_file`, `search_markdown`, or `rescan_folder`.

## Open questions

- Output shape: the intent assumed structured per-file entries. Assumption: the tool returns a list of dicts (`path`, `size_bytes`) that FastMCP serialises for the client, not a pre-formatted text summary.
- Size unit: assumed raw bytes as an integer, with no unit conversion or rounding; downstream formatting is the client's job.
- Folder scope: assumed the single configured/scanned folder of the server instance, matching what the other tools see. Serving multiple folders in one tool call is not designed here.
- Recursion: assumed all markdown files the scanner already discovers are included, including `.md`, `.markdown`, and `.mdx` anywhere under the served folder.
- Files that disappear or cannot be read between scan and call: the intent only specifies no error for an empty folder. Assumption: such files are silently omitted rather than failing the whole call.
- Existing tools: assumed the intent's "new MCP tool" means `list_files()` and other tools keep their current signatures and output.
