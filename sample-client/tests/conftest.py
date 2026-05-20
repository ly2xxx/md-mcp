"""Shared fixtures for BDD tests.

The MCP client API is async and uses ``anyio`` cancel scopes that must be
entered and exited on the same task. pytest-bdd steps are sync. We bridge
that with ``anyio.from_thread.start_blocking_portal``: a dedicated thread
runs the event loop and ``portal.wrap_async_context_manager`` keeps each
async context manager alive on a single, long-lived task — which is what
the anyio invariants require.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

import anyio.from_thread
import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Match mcpclient_llm.py's default folder.
FOLDER_TO_SERVE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test-samples")
)


@pytest.fixture(scope="session")
def mcp_portal():
    """Blocking portal that owns a long-lived asyncio loop on its own thread."""
    with anyio.from_thread.start_blocking_portal("asyncio") as portal:
        yield portal


@pytest.fixture(scope="session")
def mcp_session(mcp_portal):
    """Initialized MCP ClientSession against a freshly spawned md_mcp server."""
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

    # Each wrap_async_context_manager produces a sync CM whose __enter__
    # and __exit__ both run on the portal's single management task — that
    # is what makes anyio happy on teardown.
    with mcp_portal.wrap_async_context_manager(stdio_client(server_params)) as (read, write):
        with mcp_portal.wrap_async_context_manager(ClientSession(read, write)) as session:
            mcp_portal.call(session.initialize)
            yield session


@pytest.fixture(scope="session")
def mcp_tools(mcp_portal, mcp_session):
    """Cached list of tools exposed by the spawned server."""
    return mcp_portal.call(mcp_session.list_tools).tools


@pytest.fixture
def scenario_ctx() -> Dict[str, Any]:
    """Per-scenario mutable bag for sharing state between steps."""
    return {}
