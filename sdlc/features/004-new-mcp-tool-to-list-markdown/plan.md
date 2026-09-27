<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@8c90ff6 -->
## Approach
Add a `size_bytes` property to `MarkdownFile` and a `list_file_sizes()` tool in `create_markdown_server` that forces a content-free rescan via an extended `ensure_scanned(force=True, load_content=False)`, formats relative paths and `os.stat().st_size` bytes in the existing `list_files` style, skips `OSError` entries, and returns the exact empty-folder message.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The MCP server exposes a tool that lists the size of each Markdown file it discovers in the configured folder. | 1, 2, 3, 4, 5, 7, 8 | 2 |
| Each result entry identifies the Markdown file and reports its size in bytes. | 1, 6 | 1, 2 |
| The tool follows the same Markdown file discovery rules as existing server behavior, including nested files. | 2, 4, 8 | 2 |
| The tool returns a clear empty result when no Markdown files are present. | 3 | 2 |
| The existing tests still pass. | 9 | 2 |

## Phase 1: Add byte-size accessor to MarkdownFile
<!-- phase: 1 -->
<!-- targets: md_mcp/scanner.py, tests/test_scanner_size.py -->
<!-- frozen: md_mcp/server.py, test_read_file.py, test_file_watching.py, test_chunking.py, test_chunking_simple.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py -->

**Goal:** `MarkdownFile.size_bytes` returns `os.stat(path).st_size` and raises `OSError` when the file is missing, without changing existing scanner behaviour.

**Changes:**
- `md_mcp/scanner.py`: add this property to the `MarkdownFile` class (e.g. directly after `to_resource_dict`):

```python
    @property
    def size_bytes(self) -> int:
        """Size of this file on disk in bytes (os.stat().st_size)."""
        return os.stat(self.path).st_size
```

`os` is already imported. The property raises `OSError` (including `FileNotFoundError`) when the path cannot be stat-ed. Do not change `MarkdownScanner` or `MARKDOWN_EXTENSIONS`.

- `tests/test_scanner_size.py`: new file with these imports:

```python
import pytest
from md_mcp.scanner import MarkdownFile
```

Tests:
1. `test_size_bytes_matches_stat_for_multibyte_content`:
   - `content = "héllo 世界"`
   - `p = tmp_path / "multi.md"; p.write_text(content, encoding="utf-8")`
   - `f = MarkdownFile(p, tmp_path)`
   - `assert f.size_bytes == p.stat().st_size`
   - `assert f.size_bytes == len(content.encode("utf-8"))`
   - `assert f.size_bytes != len(content)`
2. `test_size_bytes_larger_than_read_cap_uses_stat`:
   - `content = "a" * 70000`
   - `p = tmp_path / "large.md"; p.write_text(content, encoding="utf-8")`
   - `f = MarkdownFile(p, tmp_path)`
   - `assert f.size_bytes == 70000`
   - `assert f.size_bytes == p.stat().st_size`
3. `test_size_bytes_raises_oserror_when_missing`:
   - `p = tmp_path / "gone.md"; p.write_text("x", encoding="utf-8")`
   - `f = MarkdownFile(p, tmp_path)`
   - `p.unlink()`
   - `with pytest.raises(OSError): _ = f.size_bytes`

**Definition of done:**
- [ ] `tests/test_scanner_size.py::test_size_bytes_matches_stat_for_multibyte_content`: proves spec behaviour 6 (size is on-disk byte count, not decoded length). No teardown needed.
- [ ] `tests/test_scanner_size.py::test_size_bytes_larger_than_read_cap_uses_stat`: proves spec behaviour 6 for files larger than `MD_MAX_READ_CHARS` (size is independent of any read cap).
- [ ] `tests/test_scanner_size.py::test_size_bytes_raises_oserror_when_missing`: proves the accessor raises `OSError` when the file cannot be stat-ed (the server tool will catch this for behaviour 7).
- [ ] Existing tests untouched; `md_mcp/server.py` untouched.

**Verify:**
```bash
uv run pytest tests/test_scanner_size.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Add list_file_sizes MCP tool
<!-- phase: 2 -->
<!-- targets: md_mcp/server.py, tests/test_list_file_sizes.py -->
<!-- frozen: md_mcp/scanner.py, tests/test_scanner_size.py, test_read_file.py, test_file_watching.py, test_chunking.py, test_chunking_simple.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py -->

**Goal:** `create_markdown_server` registers a `list_file_sizes()` MCP tool that rescans without loading content, returns one line per discovered Markdown file with relative path and `os.stat().st_size` bytes, skips unreadable files, and returns the exact empty-folder message.

**Changes:**
- `md_mcp/server.py`:
  1. Change the inner `ensure_scanned` function from:

```python
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
```

to:

```python
    def ensure_scanned(force: bool = False, load_content: bool = True) -> None:
        nonlocal markdown_files
        if force or not markdown_files:
            markdown_files = scanner.scan()
            logger.info(f"Scanned {len(markdown_files)} markdown files from {folder_path}")
            sys.stderr.write(f"[md-mcp] Scanned {len(markdown_files)} files from {folder_path}\n")
            sys.stderr.flush()
            if load_content:
                for md_file in markdown_files:
                    if md_file.content is None:
                        md_file.load()
```

Existing call sites (`read_file`, `rescan_folder`, `list_files`, `search_markdown`, `get_all_chunks`, etc.) remain `ensure_scanned()` and keep the old behaviour.

  2. Add a new tool immediately after `list_files` inside `create_markdown_server`:

```python
    @mcp.tool()
    def list_file_sizes() -> str:
        """List each discovered markdown file with its size in bytes.

        Returns:
            One line per markdown file, each with the file's relative path
            (forward slashes) and its size in bytes, or a message when the
            folder contains no markdown files.
        """
        ensure_scanned(force=True, load_content=False)
        if not markdown_files:
            return f"No markdown files found in {folder_path}."
        lines = []
        for md_file in markdown_files:
            path_str = str(md_file.relative_path).replace('\\', '/')
            try:
                size = md_file.size_bytes
            except OSError:
                continue
            lines.append(f"- **{path_str}** — {size} bytes")
        result = f"Found {len(lines)} markdown file(s) in {folder_path}:\n\n"
        result += "\n".join(lines)
        return result
```

  - Uses `ensure_scanned(force=True, load_content=False)` so the folder is rescanned on every call (spec behaviour 5) but content is not loaded, so an unreadable file does not raise during scan (spec behaviour 7).
  - Uses `md_file.size_bytes` from Phase 1, catches `OSError`, and skips that entry.
  - Path normalization matches existing `list_files`: `str(md_file.relative_path).replace('\\', '/')`.
  - Header style matches `list_files`: `Found {n} markdown file(s) in {folder_path}:`.
  - Empty case returns exactly `No markdown files found in {folder_path}.`.

- `tests/test_list_file_sizes.py`: new file.

Imports:

```python
import asyncio
from pathlib import Path
import pytest

from md_mcp import server as server_module
from md_mcp.server import create_markdown_server
from md_mcp.scanner import MarkdownFile
```

Helper:

```python
def _call_tool(server, name, arguments=None):
    tool = server._tool_manager.get_tool(name)
    return tool.fn(**(arguments or {}))
```

Fixture:

```python
@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(server_module, "WATCH_AVAILABLE", False)
    return create_markdown_server(str(tmp_path), server_name="test")
```

No teardown is needed because `WATCH_AVAILABLE` is forced `False`, so no watchdog observer thread starts. If telemetry middleware is installed, it is request-scoped and has no background thread; no cleanup fixture is required.

Tests:
1. `test_list_file_sizes_returns_entries_for_nested_markdown_files`:
   - create `tmp_path/a.md` with `"hello"` (5 bytes)
   - create `tmp_path/nested/b.markdown` with `"héllo 世界"` (multi-byte)
   - create `tmp_path/ignore.txt` with `"nope"`
   - `result = _call_tool(server, "list_file_sizes")`
   - assert `f"Found 2 markdown file(s) in {tmp_path}:" in result`
   - assert `"a.md"` in result and `"5 bytes"` in result
   - assert `"nested/b.markdown"` in result and `f"{(tmp_path / 'nested' / 'b.markdown').stat().st_size} bytes" in result`
   - assert `"ignore.txt" not in result`
   - assert `result.index("a.md") < result.index("nested/b.markdown")` (order from `MarkdownScanner.scan()`)
2. `test_list_file_sizes_returns_empty_message_for_empty_folder`:
   - `result = _call_tool(server, "list_file_sizes")`
   - assert `result == f"No markdown files found in {tmp_path}."`
3. `test_list_file_sizes_ignores_non_markdown_files`:
   - create `tmp_path/notes.txt`
   - `result = _call_tool(server, "list_file_sizes")`
   - assert `result == f"No markdown files found in {tmp_path}."`
4. `test_list_file_sizes_reflects_current_disk_state`:
   - create `a.md` with `"one"` (3 bytes), call, assert `"3 bytes" in result`
   - overwrite `a.md` with `"one two three"` (13 bytes), call, assert `"13 bytes" in result`
   - create `b.md` with `"new"` (3 bytes), call, assert `Found 2 markdown file(s)` and `"b.md" in result`
   - delete `a.md`, call, assert `Found 1 markdown file(s)` and `"a.md" not in result` and `"b.md" in result`
5. `test_list_file_sizes_skips_unreadable_file`:
   - `monkeypatch.setattr(server_module, "WATCH_AVAILABLE", False)`
   - create `tmp_path/a.md` with `"a"` (1 byte)
   - `missing = tmp_path / "missing.md"` (do not create)
   - `files = [MarkdownFile(tmp_path / "a.md", tmp_path), MarkdownFile(missing, tmp_path)]`
   - `monkeypatch.setattr(server_module.MarkdownScanner, "scan", lambda self: files)`
   - `server = create_markdown_server(str(tmp_path), server_name="test")`
   - `result = _call_tool(server, "list_file_sizes")`
   - assert `"a.md" in result` and `"1 bytes" in result`
   - assert `"missing.md" not in result`
   - assert `result` is a `str` and the call did not raise
6. `test_list_file_sizes_tool_is_registered`:
   - `tool = server._tool_manager.get_tool("list_file_sizes")`
   - assert `tool is not None`
   - assert `callable(tool.fn)`

**Definition of done:**
- [ ] `tests/test_list_file_sizes.py::test_list_file_sizes_returns_entries_for_nested_markdown_files`: proves spec behaviours 1, 2, 4, 6, 8.
- [ ] `tests/test_list_file_sizes.py::test_list_file_sizes_returns_empty_message_for_empty_folder`: proves spec behaviour 3.
- [ ] `tests/test_list_file_sizes.py::test_list_file_sizes_ignores_non_markdown_files`: proves spec behaviour 4.
- [ ] `tests/test_list_file_sizes.py::test_list_file_sizes_reflects_current_disk_state`: proves spec behaviour 5 (added, modified, deleted files are reflected because `ensure_scanned(force=True, load_content=False)` rescans on every call).
- [ ] `tests/test_list_file_sizes.py::test_list_file_sizes_skips_unreadable_file`: proves spec behaviour 7 (missing file's entry omitted, remaining entry returned, no raise).
- [ ] `tests/test_list_file_sizes.py::test_list_file_sizes_tool_is_registered`: proves the MCP server exposes the tool (Done when 1).
- [ ] Existing tests still pass: run `uv run pytest test_read_file.py test_file_watching.py test_chunking.py test_chunking_simple.py test_search_natural_language.py test_semantic.py test_strategy_param.py -v` (semantic tests skip when optional dependencies are absent; no network is required for the other files).

**Verify:**
```bash
uv run pytest tests/test_list_file_sizes.py tests/test_scanner_size.py -v
uv run pytest test_read_file.py test_file_watching.py test_chunking.py test_chunking_simple.py test_search_natural_language.py test_semantic.py test_strategy_param.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- `ensure_scanned` signature change could break a caller that passes positional args. All current callers use no args; Phase 2 tests and the existing-test run catch this.
- FastMCP `_tool_manager` private API may change. `tests/test_list_file_sizes.py::test_list_file_sizes_tool_is_registered` catches this. If it fails, replace `_call_tool` with `fastmcp.Client` in-memory calls.
- Watchdog observer thread could leak in tests. Phase 2 fixture monkeypatches `WATCH_AVAILABLE = False`; no observer starts. If the fixture is removed, add `server._observer.stop(); server._observer.join()` teardown.
- Existing semantic tests may need network/model downloads. The Phase 2 Verify command may fail in a fresh environment without cached models; if so, run the network-free subset and document the manual full-suite run.
- Output format mismatch (e.g. header count when unreadable files are skipped). Phase 2 tests assert header and entries.
- `size_bytes` using `os.stat` is not affected by `MD_MAX_READ_CHARS`. Phase 1 tests catch truncation-based mistakes.
- Path normalization on Windows. Phase 2 test asserts `nested/b.markdown` with forward slashes.

## Open questions
- Assumption: extending `ensure_scanned` with `force` and `load_content` is acceptable; defaults preserve existing behaviour. If not, `list_file_sizes` could call `scanner.scan()` directly, but that would duplicate scan logic and leave caches stale.
- Assumption: FastMCP exposes `server._tool_manager.get_tool(name).fn` for tests. If not, replace `_call_tool` with `fastmcp.Client` in-memory calls.
- Assumption: existing tests either do not require network or skip when optional semantic dependencies are absent. If they do require network, run only the network-free subset in automated Verify and run the full suite manually with the semantic model cache present.
- Output format for the all-unreadable edge case: returns `Found 0 markdown file(s) in {folder_path}:\n\n` rather than the empty-folder message, because Markdown files were discovered. Not explicitly specified.
