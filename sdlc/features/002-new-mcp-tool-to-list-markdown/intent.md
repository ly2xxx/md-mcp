<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@47ee98e -->
# Intent: Markdown File Size Listing Tool

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Users who expose large Markdown collections through md-mcp have no quick way to see which files are large. They must leave the AI client and inspect the filesystem manually to find oversized notes, duplicated docs, or candidates for cleanup. This slows down context auditing and makes it harder to explain why certain folders are expensive to work with.

## Outcome
The MCP server exposes a new tool that lists Markdown files and their sizes for the Markdown content it already makes available. An MCP client can call it to answer questions such as which Markdown files are largest without needing direct filesystem access. The tool most likely belongs in `md_mcp/server.py` alongside the other MCP tools.

## Done when
- An MCP client can discover and call the new Markdown file size tool.
- The result lists every Markdown file known to the configured folder or folders.
- Each listed entry identifies the file and reports its size.
- Size values are consistent and understandable, whether reported as raw bytes or human-readable units.
- An empty or missing Markdown folder produces a clear empty result or message rather than an error.
- The existing tests still pass.

## Not in scope
- Sorting, filtering, paging, or grouping beyond what is needed to list files and sizes.
- Content previews, word counts, line counts, or file modification metadata.
- Cleanup actions, deletion, or recommendations about which files to remove.
- Changes to file scanning, file watching, or folder configuration behavior.
- Web UI changes for viewing Markdown file sizes.

## Open questions
- Should the tool cover all configured folders or only the active server's folder? Assumption: it covers the same Markdown files the server already exposes.
- What unit should sizes use? Assumption: bytes are always available, with human-readable units acceptable if consistent.
- Should results be sorted? Assumption: yes, by path ascending for predictable output.
- Should hidden or excluded Markdown files appear? Assumption: only files already included by the existing scan behavior.
- No prior `intent.md` content was supplied, so this is a new intent rather than a revision of an existing one.
