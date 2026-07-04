# Changelist — July 2026 quick wins

One commit per entry; entries move to Done with a description of the actual
change as they land.

## Planned

- [ ] **`MD_CACHE_DIR` for the semantic embeddings cache** — stop writing
  `.md-mcp-embeddings.json` into the notes folder so `/data` can stay `:ro`
  even with semantic search enabled.
- [ ] **Bound `list_files` output** — add a `pattern` filter and a `limit`
  so large vaults don't produce giant responses.
- [ ] **Scanner improvements** — O(1) path lookup instead of linear scan;
  also index `.markdown` / `.mdx` files (scanner + file watcher).

## Done

- [x] **Add `read_file(path, section="")` tool** (`md_mcp/server.py`) — reads
  a full file by relative path, or only the sections whose header path
  matches `section` (case-insensitive; unmatched section returns the list of
  available sections). Unknown paths return difflib-based "did you mean"
  suggestions. Output capped at `MD_MAX_READ_CHARS` (default 60000) with a
  truncation notice pointing at the `section` argument. The search_markdown
  tip that referenced the nonexistent `read_file_section()` now points at
  `read_file`. Verified via FastMCP client: full read, nested path, section
  read, typo suggestion; existing 8-test suite passes.
