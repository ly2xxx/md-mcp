"""Focused tests for the list_file_sizes MCP tool."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
from fastmcp import Client

from md_mcp.server import create_markdown_server
from md_mcp.scanner import MarkdownFile


@pytest.fixture
def make_server(tmp_path: Path):
    """Factory fixture to create and safely tear down create_markdown_server instances."""
    servers = []

    def _make(folder: Path | None = None, name: str = "test-docs"):
        target_folder = folder or tmp_path
        server = create_markdown_server(str(target_folder), name)
        servers.append(server)
        return server

    yield _make

    for server in servers:
        if hasattr(server, "_observer") and server._observer:
            try:
                server._observer.stop()
                server._observer.join(timeout=1.0)
            except Exception:
                pass


def _extract_tool_result(result: Any) -> List[Dict[str, Any]]:
    """Parse tool call result into a list of dicts."""
    if hasattr(result, "structured_content") and result.structured_content is not None:
        data = result.structured_content
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        if isinstance(data, list):
            return data
    if hasattr(result, "data") and result.data is not None:
        data = result.data
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        if isinstance(data, list):
            return data
    if hasattr(result, "content") and result.content:
        data = json.loads(result.content[0].text)
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        if isinstance(data, list):
            return data
    return []


def test_tool_registered_with_size_description(tmp_path: Path, make_server):
    """Spec behaviour 1: Tool is exposed and description mentions listing markdown sizes."""
    server = make_server(tmp_path)

    async def run():
        async with Client(server) as client:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == "list_file_sizes"), None)
            assert tool is not None, "list_file_sizes tool was not registered"
            desc = (tool.description or "").lower()
            assert "markdown" in desc
            assert "size" in desc

    asyncio.run(run())


def test_returns_path_and_size_for_all_scanner_files(tmp_path: Path, make_server):
    """Spec behaviours 2 and 4: Returns path and size matching filesystem for all files."""
    f1 = tmp_path / "first.md"
    f2 = tmp_path / "second.markdown"
    f1.write_text("# First document\nContent here.", encoding="utf-8", newline="\n")
    f2.write_text("# Second document\nMore text goes here.", encoding="utf-8", newline="\n")

    server = make_server(tmp_path)

    async def run():
        async with Client(server) as client:
            result = await client.call_tool("list_file_sizes")
            assert not result.is_error
            entries = _extract_tool_result(result)
            assert len(entries) == 2

            entry_map = {e["path"]: e["size_bytes"] for e in entries}
            assert "first.md" in entry_map
            assert "second.markdown" in entry_map
            assert entry_map["first.md"] == f1.stat().st_size
            assert entry_map["second.markdown"] == f2.stat().st_size

    asyncio.run(run())


def test_includes_subfolders_and_only_markdown_extensions(tmp_path: Path, make_server):
    """Spec behaviour 3: Includes subfolders and only .md, .markdown, .mdx extensions."""
    # Markdown files at root and nested
    (tmp_path / "root.md").write_text("root file", encoding="utf-8", newline="\n")
    sub = tmp_path / "nested" / "subfolder"
    sub.mkdir(parents=True)
    (sub / "nested.markdown").write_text("nested content", encoding="utf-8", newline="\n")
    (sub / "special.mdx").write_text("mdx component", encoding="utf-8", newline="\n")

    # Non-markdown files that must be ignored
    (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8", newline="\n")
    (sub / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    server = make_server(tmp_path)

    async def run():
        async with Client(server) as client:
            result = await client.call_tool("list_file_sizes")
            assert not result.is_error
            entries = _extract_tool_result(result)
            paths = [e["path"] for e in entries]

            assert paths == [
                "nested/subfolder/nested.markdown",
                "nested/subfolder/special.mdx",
                "root.md",
            ]

    asyncio.run(run())


def test_deterministic_ascending_path_order(tmp_path: Path, make_server):
    """Spec behaviour 5: Identical results across calls, sorted in ascending path order."""
    (tmp_path / "z_doc.md").write_text("z", encoding="utf-8", newline="\n")
    (tmp_path / "a_doc.md").write_text("a", encoding="utf-8", newline="\n")
    sub = tmp_path / "b_folder"
    sub.mkdir()
    (sub / "item.md").write_text("b item", encoding="utf-8", newline="\n")

    server = make_server(tmp_path)

    async def run():
        async with Client(server) as client:
            res1 = await client.call_tool("list_file_sizes")
            res2 = await client.call_tool("list_file_sizes")

            entries1 = _extract_tool_result(res1)
            entries2 = _extract_tool_result(res2)

            assert entries1 == entries2
            paths = [e["path"] for e in entries1]
            assert paths == sorted(paths)
            assert paths == ["a_doc.md", "b_folder/item.md", "z_doc.md"]

    asyncio.run(run())


def test_empty_folder_returns_empty_list_without_error(tmp_path: Path, make_server):
    """Spec behaviour 6: Empty folder returns empty list without error."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    server = make_server(empty_dir)

    async def run():
        async with Client(server) as client:
            result = await client.call_tool("list_file_sizes")
            assert not result.is_error
            entries = _extract_tool_result(result)
            assert entries == []

    asyncio.run(run())


def test_missing_or_unreadable_file_is_omitted(tmp_path: Path, make_server, monkeypatch):
    """Spec behaviour 7: Unreadable or missing file is omitted without failing the call."""
    f1 = tmp_path / "good1.md"
    f2 = tmp_path / "bad.md"
    f3 = tmp_path / "good2.md"

    f1.write_text("good 1", encoding="utf-8", newline="\n")
    f2.write_text("will fail stat", encoding="utf-8", newline="\n")
    f3.write_text("good 2", encoding="utf-8", newline="\n")

    orig_get_size = MarkdownFile.get_size_bytes

    def mock_get_size_bytes(self: MarkdownFile) -> int:
        if self.path.name == "bad.md":
            raise OSError("Simulated filesystem error")
        return orig_get_size(self)

    monkeypatch.setattr(MarkdownFile, "get_size_bytes", mock_get_size_bytes)

    server = make_server(tmp_path)

    async def run():
        async with Client(server) as client:
            result = await client.call_tool("list_file_sizes")
            assert not result.is_error
            entries = _extract_tool_result(result)
            paths = [e["path"] for e in entries]

            assert "bad.md" not in paths
            assert paths == ["good1.md", "good2.md"]

    asyncio.run(run())
