<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@a03e303 -->
## Approach
Add one no-argument MCP tool, `list_file_sizes`, inside the existing `create_markdown_server` factory in `md_mcp/server.py`. It reuses the already-scanned file list (`ensure_scanned()`), normalises each `relative_path` to `/`, sorts ascending, and reports `os.path.getsize` for each file as `N bytes`; empty folders, missing folders, and unreadable files return a clear message instead of raising. No other module or existing tool changes.

## Coverage
| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| An MCP client can discover and call the new Markdown file size tool. | 1 | Phase 1 |
| The result lists every Markdown file known to the configured folder or folders. | 2, 8 | Phase 1 |
| Each listed entry identifies the file and reports its size. | 3, 7 | Phase 1 (size present), Phase 2 (size unavailable fallback) |
| Size values are consistent and understandable, whether reported as raw bytes or human-readable units. | 3 | Phase 1 |
| An empty or missing Markdown folder produces a clear empty result or message rather than an error. | 5, 6 | Phase 1 (empty folder), Phase 2 (missing folder) |
| The existing tests still pass. | 9 | Phase 1, Phase 2 |

## Phase 1: list_file_sizes tool with byte sizes and path-sorted output
<!-- phase: 1 -->
<!-- targets: md_mcp/server.py, test_list_file_sizes.py -->
<!-- frozen: test_chunking.py, test_chunking_simple.py, test_file_watching.py, test_read_file.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py, md_mcp/scanner.py, md_mcp/config.py, md_mcp/chunking.py, md_mcp/semantic.py, md_mcp/telemetry.py, md_mcp/server_runner.py, md_mcp/__main__.py, md_mcp/web/** -->

**Goal:** An MCP client that calls `list_file_sizes` on a folder of Markdown files gets one `- <relative/path.md>: <N> bytes` line per scanner-exposed file, sorted by path ascending.

**Changes:**
- `md_mcp/server.py`: inside `create_markdown_server`, after the `list_files` tool, add the spec's `@mcp.tool() def list_file_sizes() -> str` with no arguments and the spec's docstring. Body: call `ensure_scanned()`; build `entries = [(str(md_file.relative_path).replace("\\", "/"), md_file) for md_file in markdown_files]`; sort with `key=lambda e: e[0]`; if empty, return `f"No markdown files found in {folder_path}."`; otherwise emit a header plus `f"- {path_str}: {os.path.getsize(Path(folder_path).expanduser() / md_file.relative_path)} bytes"` per entry. Reuse the existing `os` and `Path` imports; do not touch `MarkdownScanner`, `MarkdownFile`, other tools, or resources.
- `test_list_file_sizes.py`: new async pytest module using the in-memory FastMCP `Client` pattern already used in `test_read_file.py`, with `tmp_path` folders containing `.md` and non-`.md` files.

**Definition of done:**
- [ ] `test_list_file_sizes.py::test_list_file_sizes_tool_is_discoverable`: proving spec behaviour 1 — the tool appears in the client's tool list and is callable with `{}`.
- [ ] `test_list_file_sizes.py::test_list_file_sizes_lists_all_scanned_files`: proving spec behaviours 2 and 8 — every path from `MarkdownScanner(tmp_path).scan()` appears, and non-Markdown files do not.
- [ ] `test_list_file_sizes.py::test_list_file_sizes_reports_bytes`: proving spec behaviour 3 — each line ends with the exact `os.path.getsize` value followed by ` bytes`.
- [ ] `test_list_file_sizes.py::test_list_file_sizes_sorted_by_relative_path`: proving spec behaviour 4 — nested paths are ordered ascending with `/` separators.
- [ ] `test_list_file_sizes.py::test_list_file_sizes_empty_folder_message`: proving spec behaviour 5 — an existing but empty folder returns a clear message and does not raise.
- [ ] Smoke MCP call over `test-samples/` prints `Found 4 markdown file(s)` and a `- getting-started.md: <N> bytes` line.
- [ ] All pre-existing root tests still pass (spec behaviour 9).

**Verify:**
```bash
uv run pytest test_list_file_sizes.py -v
uv run pytest test_chunking.py test_chunking_simple.py test_file_watching.py test_read_file.py test_search_natural_language.py test_semantic.py test_strategy_param.py -v
uv run python -c "
import asyncio
from md_mcp.server import create_markdown_server
from fastmcp import Client

async def main():
    mcp = create_markdown_server('test-samples')
    async with Client(mcp) as client:
        result = await client.call_tool('list_file_sizes', {})
        text = result.content[0].text
        assert 'getting-started.md' in text and 'bytes' in text, text
        print(text)

asyncio.run(main())
"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Harden list_file_sizes against missing folders and unreadable files
<!-- phase: 2 -->
<!-- targets: md_mcp/server.py, test_list_file_sizes.py -->
<!-- frozen: test_chunking.py, test_chunking_simple.py, test_file_watching.py, test_read_file.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py, md_mcp/scanner.py, md_mcp/config.py, md_mcp/chunking.py, md_mcp/semantic.py, md_mcp/telemetry.py, md_mcp/server_runner.py, md_mcp/__main__.py, md_mcp/web/** -->

**Goal:** Calling `list_file_sizes` against a missing folder returns a clear message, and a file whose size cannot be read is reported as unavailable while every other file is still listed.

**Changes:**
- `md_mcp/server.py`: in `list_file_sizes`, resolve `folder = Path(folder_path).expanduser()` and return `f"Markdown folder not found or inaccessible: {folder_path}"` when `folder.is_dir()` is false, before touching `ensure_scanned()`. Wrap the `ensure_scanned()` call in `try/except OSError` returning the same message. Move the per-entry `os.path.getsize` into a `try/except OSError` that appends `f"- {path_str}: size unavailable"` and continues instead of raising. Keep `os.path.getsize` as the sizing call so the test can monkeypatch it.
- `test_list_file_sizes.py`: append the two tests below, reusing the existing client/temp-dir helpers.

**Definition of done:**
- [ ] `test_list_file_sizes.py::test_list_file_sizes_missing_folder_message`: proving spec behaviour 6 — a server built on a non-existent path returns a clear missing-folder message with no unhandled error.
- [ ] `test_list_file_sizes.py::test_list_file_sizes_unavailable_size_continues`: proving spec behaviour 7 — with `os.path.getsize` raising `OSError` for one file, that file is listed with an "unavailable" marker and the other files still report their byte sizes.
- [ ] The Phase 1 tests in `test_list_file_sizes.py` still pass unmodified.
- [ ] Smoke MCP call against a non-existent folder prints a message containing "not found" or "inaccessible".

**Verify:**
```bash
uv run pytest test_list_file_sizes.py -v
uv run pytest test_chunking.py test_chunking_simple.py test_file_watching.py test_read_file.py test_search_natural_language.py test_semantic.py test_strategy_param.py -v
uv run python -c "
import asyncio
from md_mcp.server import create_markdown_server
from fastmcp import Client

async def main():
    mcp = create_markdown_server('/nonexistent-md-mcp-smoke-folder')
    async with Client(mcp) as client:
        result = await client.call_tool('list_file_sizes', {})
        text = result.content[0].text
        assert 'not found' in text.lower() or 'inaccessible' in text.lower(), text
        print(text)

asyncio.run(main())
"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- **Path reconstruction drift:** `Path(folder_path).expanduser() / md_file.relative_path` can disagree with the scanner's resolved path when symlinks or a `~` folder are involved, producing wrong sizes or a spurious "unavailable". Caught by `test_list_file_sizes_reports_bytes`; if `md_mcp/scanner.py` exposes an absolute path on `MarkdownFile`, prefer that and note it.
- **Scanner behaviour on a missing folder:** `ensure_scanned()` may raise before the guard runs. Caught by `test_list_file_sizes_missing_folder_message` in Phase 2.
- **FastMCP client API shape:** `client.call_tool(...)`/`client.list_tools()` return types vary across FastMCP versions. Caught loudly at the Phase 1 gate; adapt the helper, not the tool.
- **Monkeypatch target:** the unavailable-size test only works while the tool calls `os.path.getsize`. Moving to `Path.stat()` would silently break it; keep `os.path.getsize`.
- **Tool-count assertions in existing tests:** a test asserting the exact set of tools would fail. Caught by the Phase 1 regression run.
- **Watcher cache invalidation flakiness:** tests use fresh `tmp_path` folders and read the cache immediately; if the watcher invalidates mid-test, re-run the tool rather than rescanning the filesystem in the test.

## Open questions
- Which attribute holds a `MarkdownFile`'s absolute path? Assumption: none is assumed; the plan derives it from `Path(folder_path) / md_file.relative_path`. If `md_mcp/scanner.py` exposes one, switch to it and delete this risk.
- Are hidden `.md` files excluded by the scanner? Assumption: the tool reports exactly what the scanner exposes and adds no filtering of its own, so behaviour 8 is inherited (verified by comparing against `MarkdownScanner(...).scan()`).
- Do the `sample-client/tests` BDD tests count as "the existing tests"? Assumption: they are exercised by a separate harness; the Verify blocks run the root-level `test_*.py` files only, since the sample-client suite may need a live client.
- Are `test_semantic.py` / `test_search_natural_language.py` runnable offline without the optional embeddings extra? Assumption: they skip when the dependency is absent, as they do today; if they require network, they belong to the existing CI job, not these gates.
