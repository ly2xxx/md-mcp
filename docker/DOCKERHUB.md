# md-mcp

**Expose your local Markdown folders to Claude and any MCP client — no embeddings, no preprocessing, no uploads. Files stay on your machine; edits show up in real time.**

`md-mcp` is a lightweight [Model Context Protocol](https://modelcontextprotocol.io)
server. Point it at a folder of `.md` files and your AI assistant can search, list,
and read them as live context.

- 🔒 **Local & private** — nothing leaves your machine
- ⚡ **Real-time** — edit a file, it's instantly available (no re-indexing)
- 🧩 **Universal** — works with Claude Code, Claude Desktop, and any MCP client
- 🪶 **Zero setup** — just mount a folder and go

## Supported tags

- `latest` — current release
- `1.0.x` — pinned version tags

Image: `python:3.12-slim` base · runs as non-root (uid 10001) · transport-aware healthcheck.

## Quick start — Claude Code / Claude Desktop (recommended)

The client launches the container itself over **stdio**, so the server starts and
stops with the client and needs no extra dependencies (you already have Docker).

Pull once so the first launch is instant:

```bash
docker pull ly2xxx/md-mcp:latest
```

Add to your MCP config (`~/.claude.json` for Claude Code, or
`claude_desktop_config.json` for Claude Desktop):

```json
{
  "mcpServers": {
    "md-notes": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MD_TRANSPORT=stdio",
        "-v", "C:/Users/you/notes:/data:ro",
        "ly2xxx/md-mcp:latest"
      ]
    }
  }
}
```

Only the `-v` **source** path changes per OS:

| OS | `-v` source |
|----|-------------|
| Windows | `C:/Users/you/notes:/data:ro` |
| macOS | `/Users/you/notes:/data:ro` |
| Linux | `/home/you/notes:/data:ro` |

Reload the client — tools `search_markdown`, `list_files`, and `rescan_folder` appear
under that server.

> `MD_TRANSPORT=stdio` is required for this `command`-style config: an MCP `command`
> server talks JSON-RPC over stdin/stdout. Use `http` only with the URL style below.

## Always-on / shared (HTTP mode)

Run one long-lived container and point any number of clients at the URL:

```bash
docker run -d --name md-notes --restart unless-stopped -p 8000:8000 \
  -v /path/to/notes:/data:ro ly2xxx/md-mcp:latest
# MCP endpoint: http://localhost:8000/mcp   (config: {"type":"http","url":"http://localhost:8000/mcp"})
```

## Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `MD_FOLDER` | `/data` | Folder of Markdown files to expose (mount yours here) |
| `MD_NAME` | `markdown-docs` | Server name / `md://<name>/…` resource prefix |
| `MD_TRANSPORT` | `http` | `stdio` (client-launched) or `http` (always-on) |
| `MD_HOST` | `0.0.0.0` | Bind address (HTTP) |
| `MD_PORT` | `8000` | Bind port (HTTP) |
| `MD_PATH` | `/mcp` | MCP endpoint path (HTTP) |

Optional semantic/hybrid search is available in builds that include
`sentence-transformers`.

## Links

- **Source & full docs:** https://github.com/ly2xxx/md-mcp
- **Docker usage guide:** https://github.com/ly2xxx/md-mcp/tree/main/docker
- **Issues:** https://github.com/ly2xxx/md-mcp/issues
- **License:** MIT
