# Running md-mcp in Docker

This folder packages **md-mcp** as a small Python container so you can run it on
local Docker Desktop (and, later, any Kubernetes-based infra) instead of as a host
Python process.

The image wraps the existing server (`md_mcp.server.create_markdown_server`) with a
thin [`entrypoint.py`](entrypoint.py) that defaults to **HTTP transport** — i.e. a
long-lived, network-reachable MCP service — which is the natural shape for
container/K8s hosting. It can still run in **stdio** mode for Claude Desktop if you
prefer.

> **Reality check on "MCP contamination":** putting each MCP server in its own
> container gives you a reproducible runtime and clean K8s deployment, but it does
> **not** by itself stop two servers' similarly-named tools from being picked
> randomly by the model. That collision happens in the *client's* tool-selection
> layer. The real fix is a gateway/proxy in front of these containers that
> **namespaces tool names** (e.g. `md.search` vs `red.search`) and controls which
> servers are visible per session. Containerizing md-mcp (this folder) is step 1;
> the proxy is step 2.

---

## What's here

| File | Purpose |
|------|---------|
| [`Dockerfile`](Dockerfile) | Builds the `python:3.12-slim`-based image (non-root, healthcheck). |
| [`entrypoint.py`](entrypoint.py) | Env-configurable runner. HTTP by default; stdio optional. |
| [`docker-compose.yml`](docker-compose.yml) | One-command local run with a mounted folder. |
| [`sample-docs/`](sample-docs/) | A throwaway markdown folder so the server has something to serve out of the box. |
| `../.dockerignore` | Keeps the build context small (excludes `.venv`, `.git`, images, etc.). |

---

## Prerequisites

- Docker Desktop running (Windows/macOS/Linux).
- Build commands are run **from the repository root** — the image needs the
  `md_mcp/` package, so the build context is the repo root, not this folder.

---

## Quick start (Docker Compose — easiest)

```powershell
cd docker
docker compose up --build
```

This builds `md-mcp:local`, mounts [`sample-docs/`](sample-docs/) at `/data`, and
serves it over HTTP at:

```
http://localhost:8000/mcp
```

Point it at **your own** markdown folder instead (PowerShell):

```powershell
$env:MD_HOST_FOLDER = "C:/Users/you/notes"
docker compose up --build
```

Stop with `Ctrl+C`, then `docker compose down`.

---

## Quick start (plain `docker build` / `docker run`)

From the **repo root**:

```powershell
# 1. Build
docker build -f docker/Dockerfile -t md-mcp:local .

# 2. Run, mounting your markdown folder read-only at /data
docker run --rm -p 8000:8000 `
  -v C:/Users/you/notes:/data:ro `
  --name md-mcp md-mcp:local
```

> On Windows PowerShell the backtick `` ` `` is the line-continuation character.
> On macOS/Linux use `\` instead.

The server is now at `http://localhost:8000/mcp`.

---

## Verifying it works

**Check the container is healthy:**

```powershell
docker ps              # STATUS should show "(healthy)" after ~15s
docker logs md-mcp     # look for: Starting HTTP MCP server 'markdown-docs'
```

**Confirm the HTTP endpoint is listening** (a bare GET returns an MCP/HTTP error,
which still proves the port is up — the MCP protocol needs a proper client):

```powershell
curl.exe -i http://localhost:8000/mcp
```

**Connect a real MCP client.** Any client that supports **streamable HTTP**
transport can point at `http://localhost:8000/mcp`. For example, an `mcp.json`
that uses HTTP:

```json
{
  "servers": {
    "md-notes-docker": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Then ask the client:
- "List the markdown files in md-notes-docker"
- "Search md-notes-docker for 'docker'"
- "Read md://markdown-docs/welcome.md"

---

## Configuration (environment variables)

All behavior is controlled by env vars, so one image serves any folder without a
rebuild:

| Variable | Default | Description |
|----------|---------|-------------|
| `MD_FOLDER` | `/data` | Folder of markdown files to expose (mount your folder here). |
| `MD_NAME` | `markdown-docs` | MCP server name; also the `md://<name>/...` resource prefix. |
| `MD_TRANSPORT` | `http` | `http`, `streamable-http`, `sse`, or `stdio`. |
| `MD_HOST` | `0.0.0.0` | Bind address (HTTP transports). Keep `0.0.0.0` inside containers. |
| `MD_PORT` | `8000` | Bind port (HTTP transports). |
| `MD_PATH` | `/mcp` | URL path of the MCP endpoint. |

Example — custom name and port:

```powershell
docker run --rm -p 9000:9000 `
  -e MD_NAME=team-wiki -e MD_PORT=9000 `
  -v C:/Users/you/wiki:/data:ro `
  md-mcp:local
```

---

## Using it with Claude Desktop (stdio mode)

Claude Desktop launches MCP servers as stdio subprocesses. You can have it launch
the **container** per session instead of a host Python process. Set
`MD_TRANSPORT=stdio` and let Claude Desktop own the container lifecycle with
`docker run -i --rm`:

```json
{
  "mcpServers": {
    "md-notes-docker": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MD_TRANSPORT=stdio",
        "-v", "C:/Users/you/notes:/data:ro",
        "md-mcp:local"
      ]
    }
  }
}
```

Notes:
- `-i` (interactive) is **required** — stdio transport needs stdin attached.
- Do **not** publish a port (`-p`) in stdio mode; there is no listening socket.
- The image must be built first (`docker build ... -t md-mcp:local .`).

---

## Optional: semantic / hybrid search

Keyword search works out of the box. Semantic and hybrid strategies need
`sentence-transformers` (which pulls in PyTorch — a much larger image):

```powershell
docker build -f docker/Dockerfile --build-arg INSTALL_SEMANTIC=true -t md-mcp:semantic .
```

When using semantic search, mount the folder **writable** (drop `:ro`) so the
embedding cache can be stored alongside the docs.

---

## Notes, limits, and next steps

- **File watching:** the built-in watchdog auto-reload may not receive change
  events for bind mounts from a Windows/macOS host (a Docker Desktop limitation).
  Use the `rescan_folder()` MCP tool to refresh after editing files. Keyword search
  always re-reads on rescan.
- **Health check** targets the HTTP port; it is not meaningful in `stdio` mode.
- **Security:** runs as non-root (uid 10001); mount knowledge bases **read-only**
  (`:ro`) unless you need semantic caching.
- **Toward Kubernetes & anti-contamination:** this image is a plain streamable-http
  service, so it drops cleanly behind **ToolHive** (which governs servers, organizes
  them into groups, and runs them via a Kubernetes operator). That gateway — not the
  container boundary alone — is what actually prevents two servers' similar tools from
  colliding. See **[step2-plan.md](step2-plan.md)** for the full adoption plan
  (verified that this image meets ToolHive's streamable-http `/mcp` backend contract).
