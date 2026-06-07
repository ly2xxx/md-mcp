# Phase C — md-mcp on Kubernetes via the ToolHive Operator

Cluster-side equivalent of the local `thv run` phases: each MCP server becomes an
`MCPServer` custom resource, reconciled by the ToolHive operator into a Deployment +
proxy Service. This is the "host MCP in a container on any K8s infra" end state.

Verified against **ToolHive v0.29.1** (CLI, operator chart, and CRD
`toolhive.stacklok.dev/v1beta1`).

## Files

| File | Server | Group | Knowledge base (hostPath) |
|------|--------|-------|---------------------------|
| [md-notes.yaml](md-notes.yaml) | `md-notes` | research | `docker/sample-docs` |
| [md-runbooks.yaml](md-runbooks.yaml) | `md-runbooks` | ops | `test-samples` |

## Prerequisites

- **Kubernetes enabled in Docker Desktop** (Settings → Kubernetes → Enable, then wait
  for it to go green). Confirm: `kubectl get nodes` shows a `Ready` node.
- **helm** and **kubectl**. In this repo they were fetched to `.tools/` — add to PATH
  for the session:
  ```powershell
  $env:PATH = "C:\code\md-mcp\.tools\helm\windows-amd64;C:\code\md-mcp\.tools\thv;$env:PATH"
  ```
- The `md-mcp:local` image present in the Docker daemon (Docker Desktop's K8s shares
  it; the manifests set `imagePullPolicy: Never` so it is never pulled from a registry).

## 1. Install the operator (CRDs first, then controller)

```powershell
helm upgrade --install toolhive-operator-crds `
  oci://ghcr.io/stacklok/toolhive/toolhive-operator-crds

helm upgrade --install toolhive-operator `
  oci://ghcr.io/stacklok/toolhive/toolhive-operator `
  --namespace toolhive-system --create-namespace

kubectl -n toolhive-system rollout status deploy/toolhive-operator
```

## 2. Apply the MCPServers

```powershell
kubectl apply -f docker/k8s/md-notes.yaml
kubectl apply -f docker/k8s/md-runbooks.yaml
```

## 3. Verify

```powershell
kubectl -n toolhive-system get mcpserver
kubectl -n toolhive-system get pods,svc
kubectl -n toolhive-system logs deploy/md-notes      # expect: ... transport 'http' on .../mcp
```

Smoke-test the proxy from your host with a port-forward + MCP `initialize`:

```powershell
kubectl -n toolhive-system port-forward svc/mcp-md-notes-proxy 18080:8080
# in another shell:
$h = @{ "Content-Type"="application/json"; "Accept"="application/json, text/event-stream" }
$b = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
Invoke-WebRequest http://localhost:18080/mcp -Method POST -Headers $h -Body $b -SkipHttpErrorCheck
```
(The exact Service name is shown by `kubectl -n toolhive-system get svc`; ToolHive
names the proxy Service after the MCPServer.)

## Notes / differences from the local CLI phase

- **No port juggling.** Each pod has its own network namespace, so both servers use
  `mcpPort: 8000` — the host-port collision worked around with `MD_PORT=8001` in the
  CLI phase does not occur here.
- **hostPath is Docker-Desktop-specific.** `/run/desktop/mnt/host/c/...` maps to the
  Windows `C:\` drive. On a real cluster, replace the `hostPath` volume with a
  `PersistentVolumeClaim` or bake the docs into the image / a ConfigMap.
- **Permission profile `none`.** Keyword search needs no outbound network. Switch to
  `name: network` only if you enable semantic search (model download) and mount `/data`
  writable.
- **Groups.** The `toolhive.stacklok.io/group` label mirrors the CLI groups
  (research / ops). Client-side group scoping (the anti-contamination control) is the
  same idea as `thv client register --group` from Phase B.

## Teardown

```powershell
kubectl delete -f docker/k8s/md-runbooks.yaml -f docker/k8s/md-notes.yaml
helm uninstall toolhive-operator -n toolhive-system
helm uninstall toolhive-operator-crds
```
