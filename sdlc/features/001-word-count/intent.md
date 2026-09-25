# Intent: word count for markdown files

**Owner:** @ly2xxx · **Status:** approved

## Problem

An agent browsing a folder can't tell a two-line stub from a 5,000-word guide
without reading each file, and reading them all wastes its context window.

## Outcome

`MarkdownFile` in `md_mcp/scanner.py` can report how many words the body of a
file has, not counting its YAML frontmatter.

## Done when

- A file with frontmatter and a three-word body reports 3.
- An empty file reports 0.
- The existing tests still pass.

## Not in scope

Showing the count in the MCP tools' output. That is a later intent.
