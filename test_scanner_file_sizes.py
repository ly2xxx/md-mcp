"""Tests for MarkdownFile.get_size_bytes() scanner primitive."""

from pathlib import Path
import pytest
from md_mcp.scanner import MarkdownScanner


def test_get_size_bytes_matches_filesystem(tmp_path: Path):
    """The helper equals Path.stat().st_size for a scanned markdown file."""
    doc = tmp_path / "hello.md"
    content = "# Hello World\n\nThis is a test markdown file."
    doc.write_text(content, encoding="utf-8", newline="\n")

    scanner = MarkdownScanner(str(tmp_path))
    files = scanner.scan()

    assert len(files) == 1
    md_file = files[0]
    expected_size = doc.stat().st_size
    assert md_file.get_size_bytes() == expected_size


def test_get_size_bytes_nested_file(tmp_path: Path):
    """The helper works for a file in a subfolder."""
    sub = tmp_path / "nested" / "docs"
    sub.mkdir(parents=True)
    doc = sub / "guide.markdown"
    content = "Nested file content with utf-8 symbols: 🚀"
    doc.write_text(content, encoding="utf-8", newline="\n")

    scanner = MarkdownScanner(str(tmp_path))
    files = scanner.scan()

    assert len(files) == 1
    md_file = files[0]
    assert md_file.get_size_bytes() == doc.stat().st_size


def test_get_size_bytes_raises_for_missing_file(tmp_path: Path):
    """A deleted file raises FileNotFoundError so the server can omit it later."""
    doc = tmp_path / "ephemeral.md"
    doc.write_text("temporary content", encoding="utf-8", newline="\n")

    scanner = MarkdownScanner(str(tmp_path))
    files = scanner.scan()

    assert len(files) == 1
    md_file = files[0]

    # Delete the file after scanning
    doc.unlink()

    with pytest.raises(FileNotFoundError):
        md_file.get_size_bytes()
