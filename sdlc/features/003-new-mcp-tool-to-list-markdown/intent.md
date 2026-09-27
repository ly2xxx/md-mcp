<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@34fd7aa -->
# Intent: List Markdown File Sizes

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Users of md-mcp point the server at folders of markdown notes and docs, but have no way to see how large those files are from within their AI client. Without that, they cannot spot oversized documents that eat context, or confirm which files make up a heavy knowledge base, and must leave the conversation to check the filesystem by hand.

## Outcome
An MCP tool is available that reports the size of the markdown files md-mcp knows about, so a user can ask their AI client for file sizes and get an answer without leaving the conversation. The tool sits alongside the existing MCP tools in `md_mcp/server.py`, drawing on the file paths already discovered by `md_mcp/scanner.py`.

## Done when
- A new MCP tool is registered and discoverable by an MCP client, named and described so a user can tell it lists markdown file sizes.
- Calling the tool returns, for each markdown file in the scanned folder(s), the file's path or name together with its size.
- The returned sizes match what the filesystem reports for those same files.
- The result is deterministic for an unchanged folder, and the tool does not error when the folder contains no markdown files.
- The existing tests still pass.

## Not in scope
- Sorting, ranking, filtering by size threshold, or flagging "large" files.
- Non-markdown files, directory sizes, or disk-usage reporting.
- Persisting, caching, or exposing size history or changes over time.
- Changes to the web UI, CLI flags, or telemetry around this tool.

## Open questions
- What output shape should the tool use (structured items vs. a formatted text summary)? Assumed: structured per-file entries that an MCP client can render, consistent with existing tools.
- What size unit and rounding should be reported? Assumed: bytes as the raw value, since downstream formatting is the client's job.
- Does "list" cover all configured folders or a single folder argument? Assumed: the currently configured/scanned folder(s), matching how the other tools see the knowledge base.
- Are sizes for subfolders included recursively? Assumed: yes, all markdown files the scanner already discovers.
- Nothing changed relative to any prior intent, since no earlier `intent.md` was supplied.
