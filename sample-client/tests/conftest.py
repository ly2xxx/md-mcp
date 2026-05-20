"""Shared fixtures for BDD tests.

Spawns the md_mcp server via stdio using exactly the StdioServerParameters from
mcpclient_llm.py and exposes a session + tool list to the step definitions.

The MCP client API is async; pytest-bdd steps are sync. We bridge that by
keeping a single session-scoped event loop and driving async calls from sync
steps via ``loop.run_until_complete(...)``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict

import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Match mcpclient_llm.py's default folder.
FOLDER_TO_SERVE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test-samples")
)


@pytest.fixture(scope="session")
def mcp_loop():
    """One asyncio loop shared by the whole test session."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def mcp_session(mcp_loop):
    """Initialized MCP ClientSession against a freshly spawned md_mcp server."""
    stack = AsyncExitStack()

    async def _enter() -> ClientSession:
        env = os.environ.copy()
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m", "md_mcp.server_runner",
                "--folder", FOLDER_TO_SERVE,
                "--name", "md-client-test",
            ],
            env=env,
        )
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        return session

    session = mcp_loop.run_until_complete(_enter())
    try:
        yield session
    finally:
        mcp_loop.run_until_complete(stack.aclose())


@pytest.fixture(scope="session")
def mcp_tools(mcp_loop, mcp_session):
    """Cached list of tools exposed by the spawned server."""
    return mcp_loop.run_until_complete(mcp_session.list_tools()).tools


@pytest.fixture
def scenario_ctx() -> Dict[str, Any]:
    """Per-scenario mutable bag for sharing state between steps."""
    return {}
