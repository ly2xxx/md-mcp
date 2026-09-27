"""End-to-end MCP client tests for list_file_sizes and regression verification."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
from fastmcp import Client

from md_mcp.server import create_markdown_server


@pytest.fixture
def e2e_server(tmp_path: Path):
    """Fixture to create and cleanly tear down an e2e server instance."""
    server = create_markdown_server(str(tmp_path), "test-e2e")
    yield server, tmp_path

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


def test_mcp_client_lists_and_calls_list_file_sizes(e2e_server):
    """Spec behaviours 1 and 2 through the client boundary."""
    server, root_dir = e2e_server

    # Set up nested directory structure with markdown files
    (root_dir / "index.md").write_text("# Home\nWelcome.", encoding="utf-8", newline="\n")
    sub = root_dir / "guides" / "getting-started"
    sub.mkdir(parents=True)
    (sub / "intro.md").write_text("# Intro\nStep 1.", encoding="utf-8", newline="\n")
    (sub / "advanced.markdown").write_text("# Advanced\nDeep dive.", encoding="utf-8", newline="\n")

    async def run():
        async with Client(server) as client:
            tools = await client.list_tools()
            tool_names = [t.name for t in tools]
            assert "list_file_sizes" in tool_names

            tool = next(t for t in tools if t.name == "list_file_sizes")
            desc = (tool.description or "").lower()
            assert "size" in desc

            res = await client.call_tool("list_file_sizes")
            assert not res.is_error
            entries = _extract_tool_result(res)

            expected_paths = [
                "guides/getting-started/advanced.markdown",
                "guides/getting-started/intro.md",
                "index.md",
            ]
            actual_paths = [e["path"] for e in entries]
            assert actual_paths == expected_paths

            for entry in entries:
                file_path = root_dir / Path(entry["path"])
                assert entry["size_bytes"] == file_path.stat().st_size

    asyncio.run(run())


def test_existing_tools_remain_registered(e2e_server):
    """Verify existing tools remain registered and unchanged alongside list_file_sizes."""
    server, _ = e2e_server

    async def run():
        async with Client(server) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}

            expected_existing_tools = {
                "read_file",
                "rescan_folder",
                "list_files",
                "search_markdown",
            }

            assert expected_existing_tools.issubset(tool_names), (
                f"Missing expected existing tools. Found: {tool_names}"
            )
            assert "list_file_sizes" in tool_names

    asyncio.run(run())
