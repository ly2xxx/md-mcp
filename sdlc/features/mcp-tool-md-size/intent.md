<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@8df5a06 -->
# Intent: List Markdown File Sizes

**Owner:** @ly2xxx · **Status:** proposed (merging this PR approves it)

## Problem
Users of md-mcp expose folders of markdown notes to an AI assistant, but neither the user nor the assistant can currently see how large those files are. Without that, an assistant cannot judge which documents are cheap to read and which are too big to pull in casually, and users cannot spot bloated or stale notes in their knowledge base.

## Outcome
A new MCP tool is available on the md-mcp server that reports the size of each markdown file in the exposed folder(s), so an assistant or user can see file sizes at a glance. It lives alongside the existing tools in `md_mcp/server.py`, follows the same conventions as the other tools (registration, naming, error handling, telemetry), and returns size information per file.

## Done when
- Calling the new tool returns one entry per markdown file currently known to the server, each with the file's identity (path/name) and its size.
- The reported size matches the real size of the file on disk.
- The tool is registered and discoverable by MCP clients exactly like the existing tools, and appears in the README's tool listing.
- Files added, modified, or removed are reflected on the next call, consistent with the server's existing real-time sync behaviour.
- The existing tests still pass.

## Not in scope
- Changing how markdown files are scanned, discovered, or watched.
- Content analysis beyond size (line counts, word counts, token estimates, reading time).
- Any UI or web-dashboard presentation of file sizes.
- Aggregating, sorting, or filtering policy beyond what the result shape requires.

## Open questions
- **Ordering and shape of results:** the idea doesn't say how the list is ordered or paginated. Assumed: results are returned for all known markdown files in a single response, ordered by path, with size in bytes.
- **Human-readable sizes:** assumed the tool reports a machine-usable numeric size (bytes) rather than formatted strings like "12 KB".
- **Folder filtering:** assumed the tool covers all folders exposed to the current server instance, with no per-folder argument, matching how existing read/search tools behave.
- **No prior intent existed for this feature**, so this document is new rather than a revision.
