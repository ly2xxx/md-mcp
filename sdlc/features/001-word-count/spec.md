<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@a8b4fb7 -->
## Summary

`MarkdownFile` in `md_mcp/scanner.py` gains a `word_count` attribute that reports the number of words in a file's body with any YAML frontmatter excluded. It is populated when `load()` parses the file, so callers that already load a file for its description or content can also read its size. No MCP tool, resource dictionary, or scanner API output changes.

## Behaviour

1. Given a file with a YAML frontmatter block and a body containing exactly three whitespace-separated words, when `MarkdownFile.load()` is called, then `MarkdownFile.word_count` equals `3`.
2. Given a file whose frontmatter contains words but whose body is empty, when `load()` is called, then `word_count` equals `0`.
3. Given a file with no frontmatter, when `load()` is called, then `word_count` equals the number of whitespace-separated tokens in the whole content.
4. Given a file whose content is empty, when `load()` is called, then `word_count` equals `0`.
5. Given a body whose tokens are separated by spaces, tabs, or newlines, when `load()` is called, then each whitespace-separated token contributes exactly one to `word_count`, and leading and trailing whitespace contributes none.
6. Given a `MarkdownFile` on which `load()` has not been called, when `word_count` is read, then it is `0`.
7. Given a file that starts with `---` but does not match the existing frontmatter pattern in `_parse_frontmatter` (for example, no closing `---` delimiter), when `load()` is called, then the entire content is counted as body and no tokens are excluded.
8. Given the existing test suite, when it is run after this change, then every existing test still passes.

## Interfaces

File: `md_mcp/scanner.py`, class `MarkdownFile`.

Added attribute in `__init__`:

```python
def __init__(self, path: Path, base_path: Path) -> None:
    ...
    self.word_count: int = 0
```

Changed method in `load()` — same signature, existing parsing retained, word counting added after frontmatter and description extraction:

```python
def load(self) -> str:
    """Load and parse the markdown file."""
    ...
    self._parse_frontmatter()
    self._extract_description()
    self._count_words()
    return self.content
```

New private method:

```python
def _count_words(self) -> None:
    """Set self.word_count to the number of whitespace-separated tokens in
    the body, excluding any YAML frontmatter stripped by the same pattern
    used in _extract_description."""
```

No other signatures change. `MarkdownScanner`, `to_uri()`, and `to_resource_dict()` are untouched.

## Out of scope

- Surfacing `word_count` in MCP tool or resource output, including `to_resource_dict()` and `to_uri()`.
- Changing how frontmatter, descriptions, or content are parsed.
- Loading files eagerly during `MarkdownScanner.scan()`, `search()`, or the file watcher.
- Markdown-aware counting such as stripping headings, code fences, links, images, or punctuation.
- Character counts, reading-time estimates, stopword removal, or stemming.
- README, web UI, Docker, or Kubernetes changes.

## Open questions

- What counts as a "word"? Assumption: any whitespace-separated token in the body, after removing a complete frontmatter block with the same pattern `_extract_description` uses; markdown syntax characters inside a token are counted as part of that token.
- What is `word_count` before `load()` runs? Assumption: `0`, matching the added `int` default, and the value is only meaningful after a successful `load()`.
- How is malformed frontmatter handled? Assumption: if `_parse_frontmatter` finds no complete frontmatter block, nothing is stripped and the full content is counted.
