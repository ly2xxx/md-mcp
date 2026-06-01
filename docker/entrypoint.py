"""Container entrypoint for md-mcp.

Runs the existing FastMCP server (md_mcp.server.create_markdown_server) inside a
container. Unlike the Claude Desktop runner (stdio only), this entrypoint defaults
to **HTTP transport** so the server can run as a long-lived, network-reachable
service on Docker / Kubernetes.

All configuration is via environment variables so the same image works for any
mounted folder without rebuilding:

    MD_FOLDER     Folder of markdown files to expose          (default: /data)
    MD_NAME       MCP server name (also used in resource URIs) (default: markdown-docs)
    MD_TRANSPORT  http | streamable-http | sse | stdio        (default: http)
    MD_HOST       Bind address for HTTP transports            (default: 0.0.0.0)
    MD_PORT       Bind port for HTTP transports               (default: 8000)
    MD_PATH       URL path for the MCP endpoint               (default: /mcp)
"""

import os
import sys

from md_mcp.server import create_markdown_server


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, default)
    return value if value not in (None, "") else default


def main() -> int:
    folder = _env("MD_FOLDER", "/data")
    name = _env("MD_NAME", "markdown-docs")
    transport = _env("MD_TRANSPORT", "http").lower()

    if not os.path.isdir(folder):
        sys.stderr.write(
            f"[md-mcp] ERROR: MD_FOLDER '{folder}' does not exist inside the container.\n"
            f"[md-mcp]        Mount your markdown folder there, e.g.:\n"
            f"[md-mcp]        docker run -v /path/to/notes:/data md-mcp:local\n"
        )
        return 1

    mcp = create_markdown_server(folder, name)

    if transport == "stdio":
        # JSON-RPC over stdin/stdout: no banner (it would corrupt the stream).
        sys.stderr.write(f"[md-mcp] Starting STDIO MCP server '{name}' serving {folder}\n")
        sys.stderr.flush()
        mcp.run(transport="stdio", show_banner=False)
        return 0

    if transport not in {"http", "streamable-http", "sse"}:
        sys.stderr.write(
            f"[md-mcp] ERROR: unknown MD_TRANSPORT '{transport}'. "
            f"Use one of: http, streamable-http, sse, stdio.\n"
        )
        return 1

    host = _env("MD_HOST", "0.0.0.0")
    port = int(_env("MD_PORT", "8000"))
    path = _env("MD_PATH", "/mcp")

    sys.stderr.write(
        f"[md-mcp] Starting {transport.upper()} MCP server '{name}'\n"
        f"[md-mcp]   serving : {folder}\n"
        f"[md-mcp]   endpoint: http://{host}:{port}{path}\n"
    )
    sys.stderr.flush()

    mcp.run(transport=transport, host=host, port=port, path=path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
