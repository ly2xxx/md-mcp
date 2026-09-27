<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@715438d -->
# Intent: List Markdown File Sizes

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Users who expose local Markdown knowledge bases through md-mcp cannot easily see which Markdown files are large. This costs them time when planning what an AI assistant can read, chunk, or search within a context window. They currently have to inspect the filesystem manually outside the MCP session to find oversized documents.

## Outcome
An MCP client can request a list of Markdown file sizes from the configured folder and receive that information through a new md-mcp tool. This likely belongs in `md_mcp/server.py` alongside the existing MCP tools.

## Done when
- The MCP server exposes a tool that lists the size of each Markdown file it discovers in the configured folder.
- Each result entry identifies the Markdown file and reports its size in bytes.
- The tool follows the same Markdown file discovery rules as existing server behavior, including nested files.
- The tool returns a clear empty result when no Markdown files are present.
- The existing tests still pass.

## Not in scope
- Reading, previewing, or summarizing Markdown file contents.
- Word counts, metadata extraction, chunk counts, or other file statistics beyond size.
- Search, filtering, sorting, grouping, or size-threshold alerts.
- Changes to the Web UI, CLI, chunking, semantic search, telemetry, or deployment setup.

## Open questions
- What unit should sizes be reported in? Assumption: bytes, as a numeric value.
- Should discovery be recursive? Assumption: yes, matching the existing auto-discovery behavior for Markdown files.
- What should the result shape be? Assumption: a list of entries, each containing a file path or identifier and its size.
- Should results be sorted? Assumption: no special sorting is required beyond whatever order existing discovery already provides.
