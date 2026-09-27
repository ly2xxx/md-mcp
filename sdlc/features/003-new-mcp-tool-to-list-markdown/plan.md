<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@a8e30fb -->
## Approach
Add a read-only `MarkdownFile.get_size_bytes()` helper and a no-argument `list_file_sizes` MCP tool in `create_markdown_server`. The tool will call `scanner.scan()` directly so it never loads file content, build `{"path": forward-slash relative path, "size_bytes": int}` entries, skip files whose stat fails, sort by path, and return `[]` for an empty folder; existing tools and their cache/load path stay untouched.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| A new MCP tool is registered and discoverable by an MCP client, named and described so a user can tell it lists markdown file sizes. | 1 | Phase 2 |
| Calling the tool returns, for each markdown file in the scanned folder(s), the file's path or name together with its size. | 2, 3, 7 | Phase 2 |
| The returned sizes match what the filesystem reports for those same files. | 4 | Phase 2 |
| The result is deterministic for an unchanged folder, and the tool does not error when the folder contains no markdown files. | 5, 6 | Phase 2 |
| The existing tests still pass. | 8 | Phase 3 |

## Phase 1: Add scanner size primitive
<!-- phase: 1 -->
<!-- targets: md_mcp/scanner.py, test_scanner_file_sizes.py -->
<!-- frozen: test_chunking.py, test_chunking_simple.py, test_file_watching.py, test_read_file.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py, sample-client/tests/**, md_mcp/server.py -->

**Goal:** `MarkdownFile.get_size_bytes()` returns `path.stat().st_size` for an existing file and raises when the file cannot be statted.

**Changes:**
- `md_mcp/scanner.py`: add `get_size_bytes(self) -> int` next to `to_uri` / `to_resource_dict`; return `self.path.stat().st_size`. Do not catch errors here.
- `test_scanner_file_sizes.py`: add focused tests using `tmp_path` and `MarkdownScanner` for a known file, a nested file, and a missing file.

**Definition of done:**
- [ ] `test_scanner_file_sizes.py::test_get_size_bytes_matches_filesystem`: the helper equals `Path.stat().st_size` for a scanned markdown file.
- [ ] `test_scanner_file_sizes.py::test_get_size_bytes_nested_file`: the helper works for a file in a subfolder.
- [ ] `test_scanner_file_sizes.py::test_get_size_bytes_raises_for_missing_file`: a deleted file raises `FileNotFoundError` so the server can omit it later.

**Verify:**
```bash
uv run pytest test_scanner_file_sizes.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Register list_file_sizes MCP tool
<!-- phase: 2 -->
<!-- targets: md_mcp/server.py, test_list_file_sizes_tool.py -->
<!-- frozen: test_chunking.py, test_chunking_simple.py, test_file_watching.py, test_read_file.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py, test_scanner_file_sizes.py, sample-client/tests/**, md_mcp/scanner.py -->

**Goal:** An MCP client can discover `list_file_sizes`, and calling it returns sorted `{"path","size_bytes"}` entries for the scanner's markdown files while skipping files whose size cannot be read.

**Changes:**
- `md_mcp/server.py`: extend the typing import to `from typing import Any, Dict, List, Optional`; add `@mcp.tool()` `list_file_sizes() -> List[Dict[str, Any]]` inside `create_markdown_server` with the spec's description. Call `scanner.scan()` directly (not `ensure_scanned()`) so the tool never loads content; for each file build `{"path": str(md_file.relative_path).replace('\\', '/'), "size_bytes": md_file.get_size_bytes()}`, catch `OSError` per file and skip it, sort entries by `path`, and return the list.
- `test_list_file_sizes_tool.py`: add focused tests with a FastMCP client and temporary folders. Cover tool registration/description, path/size correctness against `Path.stat().st_size`, recursive `.md` / `.markdown` / `.mdx` inclusion and non-markdown exclusion, deterministic ascending order across two calls, empty folder returning `[]`, and a monkeypatched `get_size_bytes` raising `OSError` for one file while the call still succeeds with the others.

**Definition of done:**
- [ ] `test_list_file_sizes_tool.py::test_tool_registered_with_size_description`: spec behaviour 1.
- [ ] `test_list_file_sizes_tool.py::test_returns_path_and_size_for_all_scanner_files`: spec behaviours 2 and 4.
- [ ] `test_list_file_sizes_tool.py::test_includes_subfolders_and_only_markdown_extensions`: spec behaviour 3.
- [ ] `test_list_file_sizes_tool.py::test_deterministic_ascending_path_order`: spec behaviour 5.
- [ ] `test_list_file_sizes_tool.py::test_empty_folder_returns_empty_list_without_error`: spec behaviour 6.
- [ ] `test_list_file_sizes_tool.py::test_missing_or_unreadable_file_is_omitted`: spec behaviour 7.

**Verify:**
```bash
uv run pytest test_list_file_sizes_tool.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: End-to-end MCP client and regression gate
<!-- phase: 3 -->
<!-- targets: test_list_file_sizes_e2e.py -->
<!-- frozen: test_chunking.py, test_chunking_simple.py, test_file_watching.py, test_read_file.py, test_search_natural_language.py, test_semantic.py, test_strategy_param.py, test_scanner_file_sizes.py, test_list_file_sizes_tool.py, sample-client/tests/**, md_mcp/scanner.py, md_mcp/server.py -->

**Goal:** A real in-memory MCP client can list and call `list_file_sizes`, existing tools remain registered, and all root tests pass.

**Changes:**
- `test_list_file_sizes_e2e.py`: add an end-to-end test that creates a temporary nested markdown folder, builds `create_markdown_server`, uses FastMCP's in-memory `Client` to list tools and call `list_file_sizes`, asserts the result, and asserts the existing tools `read_file`, `rescan_folder`, `list_files`, and `search_markdown` are still present. Stop the server's watcher in teardown.

**Definition of done:**
- [ ] `test_list_file_sizes_e2e.py::test_mcp_client_lists_and_calls_list_file_sizes`: spec behaviours 1 and 2 through the client boundary.
- [ ] `test_list_file_sizes_e2e.py::test_existing_tools_remain_registered`: existing tool names are unchanged.
- [ ] `uv run pytest test_*.py -v` exits zero and reports no failures.

**Verify:**
```bash
uv run pytest test_list_file_sizes_e2e.py -v
uv run pytest test_*.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- `list_file_sizes` calls `scanner.scan()` directly instead of `ensure_scanned()` to avoid content-load failures; this refreshes the scanner's internal list. Phase 3's full root suite and e2e test catch any existing-tool regression.
- A file that disappears or cannot be statted between scan and size lookup must not fail the whole call; Phase 1's missing-file test and Phase 2's monkeypatched omission test catch this.
- Path ordering and Windows/Linux separator differences; Phase 2's order/path test and Phase 3's client test catch this.
- FastMCP client API differences in the pinned version; Phase 2 and Phase 3 tests would fail, and the open question gives the fallback.
- Watcher threads leaking during tests; each new test must stop `mcp._observer` in teardown; Phase 2/3 tests catch by hanging or failing.
- The root `test_*.py` glob may not match the project's intended full suite if configuration changes; Phase 3 open question covers the assumption.

## Open questions
- MCP test harness: assume the pinned FastMCP version supports in-memory `Client(mcp)` for `list_tools()` and `call_tool()`. If it does not, the fallback is the project's existing MCP test helper or the tool manager used by existing tests.
- Regression scope: assume "existing tests" means the root `test_*.py` files; `sample-client/tests/**` is a separate BDD suite that may require a running client/LLM and is therefore frozen but not run by the Phase 3 Verify command.
- Error handling: assume `MarkdownFile.get_size_bytes()` propagates `OSError` / `FileNotFoundError` and `list_file_sizes` catches `OSError` per entry, omitting that file.
