# Changelist — July 2026 quick wins

One commit per entry; entries move to Done with a description of the actual
change as they land.

## Planned

## Done

- [x] **v1.0.6: natural-language keyword search fix** (`md_mcp/chunking.py`) —
  `search_chunks` (the default `strategy="keyword"` of `search_markdown`)
  required the ENTIRE query to appear verbatim in a chunk, so the
  natural-language questions LLM callers actually send ("what is the logical
  execution order of a SQL SELECT query?") returned zero results against
  notes that contained the answer. Now matches on exact phrase OR any
  content-bearing query term (new `_query_terms()` strips stopwords);
  `calculate_relevance` scores per-term frequency (capped per term) with
  exact-phrase bonuses (+3 content / +2 header) so verbatim matches still
  rank on top; `extract_snippet` anchors on the line with the most query
  terms instead of falling back to the first lines. Found live: the
  langgraph_ollama RAG agent's md-mcp searches all came back empty and the
  model answered from parametric knowledge instead of the notes. New
  regression suite `test_search_natural_language.py`; existing chunking
  tests pass. Also fixed `md_mcp/__init__.py` `__version__` which had been
  stuck at 1.0.4 since the 1.0.5 release (bump script's sed matched nothing).

- [x] **Scanner improvements** — `MarkdownScanner` now indexes `.md`,
  `.markdown` and `.mdx` (new shared `MARKDOWN_EXTENSIONS` constant) and
  builds a relative-path dict during `scan()`, making
  `get_file_by_relative_path` O(1) instead of a linear scan. The file
  watcher's event filter uses the same extension set (it previously only
  reacted to `.md`, so `.markdown`/`.mdx` edits would not have invalidated
  the cache). Scan order is now sorted for deterministic listings. Not
  changed: frontmatter parsing — flagged earlier as mangling colon values,
  but it already uses `split(':', 1)`, so no fix was needed.

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
