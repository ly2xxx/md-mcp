# Step 2 — Adopting ToolHive for md-mcp

**Goal:** put the containerized `md-mcp` (step 1, see [README.md](README.md)) behind
**[ToolHive](https://github.com/stacklok/toolhive)** so that multiple MCP servers can
run side-by-side **without tool contamination** — the problem you hit where two
servers expose similarly-described tools and the model picks one at random.

> **Why ToolHive fixes contamination and a bare container doesn't:** the collision
> happens in the *client's* tool-selection step, not in the server runtime. ToolHive
> sits in front of each server as a transparent proxy, runs each in its own
> sandbox, organizes them into **groups**, and lets you control which servers a given
> client sees. Combined with per-server naming, the model is no longer handed two
> indistinguishable tools in the same context.

---

## 0. What already conforms (verified)

ToolHive runs a containerized MCP server by starting the image and proxying client
traffic to a container port. For `streamable-http` it **preserves the request path**
and detects the MCP endpoint via `HasPrefix(path, "/mcp")`
(`pkg/transport/proxy/transparent/transparent_proxy.go`). Our image already matches
that contract:

| ToolHive expectation | md-mcp image | Status |
|----------------------|--------------|--------|
| Listens on `0.0.0.0` | `MD_HOST=0.0.0.0` | ✅ |
| Serves `streamable-http` | `MD_TRANSPORT=http` (FastMCP serves streamable-http) | ✅ |
| Endpoint under `/mcp` | `MD_PATH=/mcp` | ✅ |
| Backend on a known port | `MD_PORT=8000` | ✅ |
| Non-root | `uid 10001` | ✅ |
| OCI metadata for catalog | `org.opencontainers.image.*` labels | ✅ (added in step 1) |

**Verified locally:** running the image with `MD_TRANSPORT=streamable-http` answers a
real MCP `initialize` handshake with HTTP 200 at `http://localhost:8000/mcp`. That is
exactly the backend ToolHive forwards to — so no code or path changes are required.

> The commands below that invoke `thv`, the operator, or `kubectl` have **not** been
> run in this repo (ToolHive isn't installed here). They are written against
> ToolHive's documented CLI flags and the `MCPServer` CRD source. Treat them as a
> tested-shaped recipe to execute, not as captured output.

---

## 1. Prerequisites

- Docker Desktop running, and the image built (from repo root):
  ```powershell
  docker build -f docker/Dockerfile -t md-mcp:local .
  ```
- ToolHive CLI (`thv`). Install per [docs.stacklok.com/toolhive](https://docs.stacklok.com/toolhive/)
  (Homebrew, WinGet, or a release binary from
  [github.com/stacklok/toolhive/releases](https://github.com/stacklok/toolhive/releases)).
- For the Kubernetes phase: a cluster (Docker Desktop's built-in K8s is fine) + Helm.

Confirm the CLI:
```powershell
thv version
```

---

## 2. Phase A — Run md-mcp under ToolHive locally (CLI)

ToolHive can run a **local** image directly. The backend port our server listens on
is `8000`, so tell ToolHive to forward there with `--target-port`.

```powershell
thv run `
  --name md-notes `
  --transport streamable-http `
  --target-port 8000 `
  --volume C:/Users/you/notes:/data:ro `
  md-mcp:local
```

What each flag does:
- `--transport streamable-http` — how ToolHive talks to the backend (matches our image).
- `--target-port 8000` — the container port our server listens on (our `MD_PORT`).
  If you change this, also pass the container env so they stay equal, e.g.
  `--env MD_PORT=9000 --target-port 9000` (check `thv run --help` for the exact env flag).
- `--volume HOST:/data:ro` — mounts your markdown at `/data` (our `MD_FOLDER` default).
  Drop `:ro` only if you enable semantic search (it writes an embedding cache).

Verify and wire up a client:
```powershell
thv list                          # md-notes should be Running; note its proxy URL
thv registry list                 # (optional) browse the built-in catalog
thv client setup                  # register ToolHive-managed servers with your MCP client
```

ToolHive now exposes `md-notes` through its proxy. Point your MCP client at the URL
`thv list` reports (a `streamable-http` endpoint on the proxy port), **not** directly
at `localhost:8000` anymore — that indirection is what lets ToolHive govern the server.

Stop it with:
```powershell
thv stop md-notes
thv rm md-notes
```

---

## 3. Phase B — The actual win: two servers, no contamination

This is the scenario from the podcast that motivated the whole exercise. Run a
second server whose tools overlap with md-mcp's (e.g. another markdown/search
server), and use ToolHive to keep them from colliding.

```powershell
# Same image, a different knowledge base, a distinct name + group
thv run --name md-notes  --group personal --transport streamable-http --target-port 8000 `
  --volume C:/Users/you/notes:/data:ro md-mcp:local

thv run --name md-runbooks --group ops    --transport streamable-http --target-port 8000 `
  --volume C:/Users/you/runbooks:/data:ro md-mcp:local
```

How this removes the contamination you experienced:

1. **Distinct workload names** — each server is `md-notes` / `md-runbooks`, so even
   identical tool names (`search_markdown`, `list_files`) are disambiguated by their
   owning server rather than merged into one undifferentiated pool.
2. **Groups** — `--group personal` vs `--group ops` lets you expose only one group to
   a given client/session, so the model never sees both `search_markdown` tools at
   once. (Confirm group flags with `thv run --help` / `thv group --help`; group
   support and naming have evolved across releases.)
3. **Per-client visibility** — `thv client` controls which servers a client is wired
   to. Narrow the surface area → fewer ambiguous tools in context.

> Practical guidance: the cleanest anti-contamination setup is **one group per client
> persona**, exposing only the handful of servers that persona needs. Contamination is
> ultimately a function of how many similar tools share a single model context;
> ToolHive's job is to keep that number small and the owners distinct.

---

## 4. Phase C — Kubernetes (the ToolHive Operator)

For "host MCP in a container on any K8s infra" (your original idea), use the
operator. It manages an `MCPServer` custom resource and runs each server as a
governed workload.

### 4a. Install the operator

```powershell
helm upgrade --install toolhive-operator-crds oci://ghcr.io/stacklok/toolhive/toolhive-operator-crds
helm upgrade --install toolhive-operator     oci://ghcr.io/stacklok/toolhive/toolhive-operator `
  --namespace toolhive-system --create-namespace
```
(Chart names/coordinates per the ToolHive K8s guide — verify against the docs for
your version.)

### 4b. Make the image available to the cluster

`md-mcp:local` lives in your local Docker daemon. Docker Desktop's K8s shares that
daemon, so set `imagePullPolicy: Never` (below) or push to a registry the cluster can
reach (`docker tag md-mcp:local <registry>/md-mcp:1.0.4 && docker push ...`).

### 4c. `MCPServer` manifest

```yaml
# md-mcp-server.yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPServer
metadata:
  name: md-notes
  namespace: toolhive-system
spec:
  image: md-mcp:local
  transport: streamable-http
  mcpPort: 8000          # the port our server listens on inside the container
  proxyPort: 8080        # the port ToolHive's proxy exposes (default)
  # Keyword search needs no outbound network → lock it down.
  # Switch to name: network if you enable semantic search (model download).
  permissionProfile:
    type: builtin
    name: none
  resources:
    limits:   { cpu: "250m", memory: "256Mi" }
    requests: { cpu: "50m",  memory: "64Mi" }
  # Provide the markdown to the pod. hostPath shown for Docker Desktop K8s;
  # in a real cluster use a PVC or a ConfigMap of docs instead.
  volumes:
    - name: notes
      hostPath: /run/desktop/mnt/host/c/Users/you/notes
      mountPath: /data
      readOnly: true
  # If using imagePullPolicy: Never for a local image, set it via podTemplateSpec:
  podTemplateSpec:
    spec:
      containers:
        - name: mcp
          imagePullPolicy: Never
```

Apply and verify:
```powershell
kubectl apply -f md-mcp-server.yaml
kubectl -n toolhive-system get mcpserver
kubectl -n toolhive-system get pods -l toolhive.stacklok.dev/name=md-notes
kubectl -n toolhive-system logs deploy/md-notes   # expect: Starting ... transport 'http' on .../mcp
```

For a second, non-colliding server, apply another `MCPServer` with a different
`metadata.name` and its own volume — the operator gives each its own Service/proxy,
which is the cluster-side equivalent of Phase B's separation.

> **Field reference (from the CRD source, `cmd/thv-operator/api/v1beta1`):**
> `image` (required), `transport` ∈ {`stdio`,`streamable-http`,`sse`} (default
> `stdio`), `mcpPort`, `proxyPort` (default 8080), `args`, `env` (`{name,value}`),
> `volumes` (`{name,hostPath,mountPath,readOnly}`), `resources`
> (`limits/requests.{cpu,memory}`), `permissionProfile` (`type` ∈
> {`builtin`,`configmap`}; builtin `name` ∈ {`none`,`network`}), `podTemplateSpec`,
> plus auth/telemetry/rate-limit refs for production hardening.

---

## 5. Permission profiles & semantic search

- **Keyword mode (default):** no outbound network, read-only `/data`. Use builtin
  profile `none`. This is the most contamination- *and* exfiltration-resistant setup.
- **Semantic / hybrid mode:** build the image with `--build-arg INSTALL_SEMANTIC=true`,
  mount `/data` **writable** (embedding cache), and allow network for the first-run
  model download → builtin profile `network` (or a `configmap` profile scoped to the
  model host). Prefer pre-baking the model into the image to keep the profile `none`.

---

## 6. Optional — publish to a registry/catalog

To make `md-mcp` discoverable via `thv run md-mcp` (instead of an explicit image
ref), add an entry to a ToolHive registry (see
[stacklok/toolhive-catalog](https://github.com/stacklok/toolhive-catalog)) describing
the image, `transport: streamable-http`, target port `8000`, required volume, and a
permission profile. Not needed for the POC — the explicit-image commands above are
enough — but it's the path to sharing it across a team.

---

## 7. Open items to confirm when you run it

- **Exact env flag** for `thv run` (`--env` vs `-e`) and **group** subcommands — pin
  against the `thv` version you install (`thv run --help`, `thv group --help`).
- **Operator chart coordinates** and the **MCPServer status/label conventions** for
  your operator version (the CRD group `toolhive.stacklok.dev/v1beta1` is from current
  `main`).
- **Local-image pull policy** in the operator — confirm `podTemplateSpec` override
  takes effect, or push to a registry the cluster can pull from.
- Whether you want **one group per client persona** (recommended) vs. a flat list.

---

## 8. Suggested order of execution

1. `docker build` the image (done in step 1).
2. Phase A: `thv run` one server, wire a client, confirm a search works through the proxy.
3. Phase B: add a second overlapping server in a different group; confirm your client
   only sees the intended tools — this is the contamination test.
4. Phase C: install the operator and re-create both as `MCPServer` resources.
5. Decide on permission profiles and (optionally) catalog publishing.
