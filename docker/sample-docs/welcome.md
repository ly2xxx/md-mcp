---
title: Welcome to md-mcp in Docker
description: A sample document proving the containerized md-mcp server works.
tags: [sample, docker, getting-started]
---

# Welcome to md-mcp (Dockerized)

If you can search for or read this file through an MCP client, your containerized
**md-mcp** server is working.

## Try these

- Ask your MCP client to **list files** — you should see `welcome.md`.
- **Search** for the word `docker` — this section should match.
- **Read** `md://markdown-docs/welcome.md` to get this whole file.

## Why containerize?

Running md-mcp in its own image gives you a reproducible runtime and a clean path
to Kubernetes. Note that container isolation alone does not prevent *tool
contamination* between MCP servers — that is solved at the client/gateway layer by
namespacing tool names, not by the container boundary.

Replace this folder by mounting your own markdown directory at `/data`.
