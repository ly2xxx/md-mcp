# Changelist — July 2026 quick wins

One commit per entry; entries move to Done with a description of the actual
change as they land.

## Planned

- [ ] **Scanner improvements** — O(1) path lookup instead of linear scan;
  also index `.markdown` / `.mdx` files (scanner + file watcher).

## Done

- [x] **Bound `list_files` output** — `list_files(pattern="", limit=100)`:
  case-insensitive substring filter, or glob when the pattern contains
  `*?[` (e.g. `projects/*.md`); output capped at `limit` with a "showing
  first N" note and total count. Empty matches suggest retrying without a
  pattern. Verified: substring, glob, limit truncation, and no-match paths.

- [x] **`MD_CACHE_DIR` for the semantic embeddings cache** — new
  `_semantic_cache_dir()` in `md_mcp/server.py`: the cache now lives at
  `$MD_CACHE_DIR` (default `~/.cache/md-mcp`) under a per-folder digest
  subdirectory, never inside the served notes folder. The notes mount can now
  always stay `:ro`; docker-compose comment and docker/README semantic
  section updated (including how to persist the cache with a named volume).
  Note: existing caches written into notes folders are simply abandoned —
  first semantic query re-embeds once into the new location.

- [x] **Add `read_file(path, section="")` tool** (`md_mcp/server.py`) — reads
  a full file by relative path, or only the sections whose header path
  matches `section` (case-insensitive; unmatched section returns the list of
  available sections). Unknown paths return difflib-based "did you mean"
  suggestions. Output capped at `MD_MAX_READ_CHARS` (default 60000) with a
  truncation notice pointing at the `section` argument. The search_markdown
  tip that referenced the nonexistent `read_file_section()` now points at
  `read_file`. Verified via FastMCP client: full read, nested path, section
  read, typo suggestion; existing 8-test suite passes.
