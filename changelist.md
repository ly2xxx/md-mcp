# Changelist — July 2026 quick wins

One commit per entry; entries move to Done with a description of the actual
change as they land.

## Planned

- [ ] **Add `read_file(path, section=None)` tool** — the LLM currently gets
  search snippets but has no tool to read a full file (resources aren't
  surfaced by many MCP clients), and the search output tip references a
  nonexistent `read_file_section()` tool.
- [ ] **`MD_CACHE_DIR` for the semantic embeddings cache** — stop writing
  `.md-mcp-embeddings.json` into the notes folder so `/data` can stay `:ro`
  even with semantic search enabled.
- [ ] **Bound `list_files` output** — add a `pattern` filter and a `limit`
  so large vaults don't produce giant responses.
- [ ] **Scanner improvements** — O(1) path lookup instead of linear scan;
  also index `.markdown` / `.mdx` files (scanner + file watcher).

## Done

(entries move here as they land)
