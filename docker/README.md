# Running md-mcp in Docker

This folder packages **md-mcp** as a small Python container so you can run it on
local Docker Desktop (and, later, any Kubernetes-based infra) instead of as a host
Python process.

The image wraps the existing server (`md_mcp.server.create_markdown_server`) with a
thin [`entrypoint.py`](entrypoint.py) supporting two styles, selected by
`MD_TRANSPORT`:

- **stdio** (`MD_TRANSPORT=stdio`) — the client launches the container and talks over
  the subprocess's stdin/stdout. **This is the recommended, dependency-free way to use
  md-mcp with Claude Code / Claude Desktop** (see the next section).
- **HTTP** (`MD_TRANSPORT=http`, the image default) — a long-lived, network-reachable
  MCP service; the natural shape for an always-on / multi-client setup and for K8s.

The public image is on Docker Hub as **`ly2xxx/md-mcp:latest`** — pull and go.

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
| [`entrypoint.py`](entrypoint.py) | Env-configurable runner (stdio or HTTP). |
| [`healthcheck.py`](healthcheck.py) | Transport-aware container healthcheck (passes in stdio mode, probes the port in HTTP mode). |
| [`docker-compose.yml`](docker-compose.yml) | One-command local run with a mounted folder (HTTP). |
| [`sample-docs/`](sample-docs/) | A throwaway markdown folder so the server has something to serve out of the box. |
| `../.dockerignore` | Keeps the build context small (excludes `.venv`, `.git`, images, etc.). |

---

## Prerequisites

- Docker Desktop running (Windows/macOS/Linux).
- Build commands are run **from the repository root** — the image needs the
  `md_mcp/` package, so the build context is the repo root, not this folder.

---

## Use with Claude Code & Claude Desktop (recommended — stdio, pull-and-go)

The simplest way to use md-mcp with an AI client: let the **client launch the
container** over stdio. The server's lifecycle is then tied to the client (starts when
the client starts, stops when it stops via `--rm`), and there are **no extra
dependencies** — if you can pull the image, you already have Docker. No `npx`/Node, no
ports to manage, no container to start or stop yourself.

One-time pull (so the first launch doesn't appear to stall while Docker fetches the
image):

```bash
docker pull ly2xxx/md-mcp:latest
```

Then add to your client's MCP config — `~/.claude.json` (Claude Code) or
`claude_desktop_config.json` (Claude Desktop):

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

Only the `-v` **source** path changes per OS — the rest is identical:

| OS | `-v` source example |
|----|---------------------|
| Windows | `C:/Users/you/notes:/data:ro` |
| macOS | `/Users/you/notes:/data:ro` |
| Linux | `/home/you/notes:/data:ro` |

Restart/reload the client; the tools (`search_markdown`, `list_files`,
`rescan_folder`) appear under that server. Add more servers by repeating the block
with a different name + folder.

Notes:
- `-i` (interactive) is **required** — stdio needs stdin attached.
- Do **not** add `-p` (no listening port exists in stdio mode).
- `MD_TRANSPORT=stdio` is mandatory here. With `http`, the server would bind a TCP
  port and ignore stdin, so the client's handshake never completes.

> **Which style should I use?**
> | | `command` + `MD_TRANSPORT=stdio` (this section) | `url` + `type:http` (below) |
> |---|---|---|
> | Who runs the container | the client, automatically | you (`docker run -d`) |
> | Lifecycle | dies with the client | long-lived, survives client restarts |
> | Extra deps | none | none (client connects by URL) |
> | Best for | single-user desktop, pull-and-go | always-on / multiple clients sharing one server |

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

**Connect a real MCP client.** Any client that supports **streamable HTTP** transport can point directly at `http://localhost:8000/mcp`. 

For generic HTTP/SSE-compatible clients (like VS Code MCP extensions using `mcp.json`):

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

For **Claude Desktop** (which only natively supports stdio subprocesses), you can connect to the running container by using `mcp-remote` as a bridge/proxy in your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "md-notes-docker": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp"
      ]
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

## Using a locally-built image instead of the published one

The recommended stdio config above uses the published `ly2xxx/md-mcp:latest`. If you
build the image yourself (e.g. to test a change), just swap the image reference for
`md-mcp:local`:

```powershell
docker build -f docker/Dockerfile -t md-mcp:local .   # from the repo root
```
```json
"args": ["run","-i","--rm","-e","MD_TRANSPORT=stdio","-v","C:/Users/you/notes:/data:ro","md-mcp:local"]
```

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
- **Health check** is transport-aware ([`healthcheck.py`](healthcheck.py)): it probes
  the TCP port in HTTP mode and passes automatically in `stdio` mode (no port to probe),
  so stdio containers no longer show a misleading "unhealthy" status.
- **Security:** runs as non-root (uid 10001); mount knowledge bases **read-only**
  (`:ro`) unless you need semantic caching.
- **Toward Kubernetes & anti-contamination:** this image is a plain streamable-http
  service, so it drops cleanly behind **ToolHive** (which governs servers, organizes
  them into groups, and runs them via a Kubernetes operator). That gateway — not the
  container boundary alone — is what actually prevents two servers' similar tools from
  colliding. See **[step2-plan.md](step2-plan.md)** for the full adoption plan
  (verified that this image meets ToolHive's streamable-http `/mcp` backend contract).
