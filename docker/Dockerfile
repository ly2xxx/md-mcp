# syntax=docker/dockerfile:1

# md-mcp container image
# -----------------------
# Build from the REPO ROOT (the build context must include the md_mcp package):
#
#     docker build -f docker/Dockerfile -t md-mcp:local .
#
# Add experimental semantic / hybrid search (pulls in torch — large image):
#
#     docker build -f docker/Dockerfile --build-arg INSTALL_SEMANTIC=true -t md-mcp:semantic .

FROM python:3.12-slim AS base

# - PYTHONUNBUFFERED      : logs/stderr appear immediately (important for stdio + docker logs)
# - PYTHONDONTWRITEBYTECODE: no .pyc clutter in the image
# - PIP_NO_CACHE_DIR      : smaller image
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy only what `pip install .` needs first, so dependency layers stay cached
# across source-only changes.
COPY pyproject.toml README.md ./
COPY md_mcp ./md_mcp

# Default: lightweight install (fastmcp, flask, watchdog).
# Set INSTALL_SEMANTIC=true to also install sentence-transformers (heavy).
# Set INSTALL_OBSERVABILITY=true to bake in OpenTelemetry export (small; the
# telemetry module is a no-op unless the OTEL packages are installed AND a
# collector is reachable, so this is safe to enable by default).
ARG INSTALL_SEMANTIC=false
ARG INSTALL_OBSERVABILITY=true
RUN pip install --upgrade pip && \
    EXTRAS=""; \
    if [ "$INSTALL_SEMANTIC" = "true" ]; then EXTRAS="semantic"; fi; \
    if [ "$INSTALL_OBSERVABILITY" = "true" ]; then \
        if [ -n "$EXTRAS" ]; then EXTRAS="$EXTRAS,observability"; else EXTRAS="observability"; fi; \
    fi; \
    if [ -n "$EXTRAS" ]; then \
        pip install ".[$EXTRAS]"; \
    else \
        pip install .; \
    fi

# Container entrypoint (HTTP-by-default runner).
COPY docker/entrypoint.py ./entrypoint.py

# OCI image metadata — standard labels consumed by registries and the ToolHive
# catalog. Override at build time, e.g.:
#   --build-arg VCS_REF=$(git rev-parse --short HEAD) --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ARG MD_MCP_VERSION=1.0.5
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="md-mcp" \
      org.opencontainers.image.description="Expose local markdown folders as an MCP server (streamable-http at /mcp)." \
      org.opencontainers.image.source="https://github.com/ly2xxx/md-mcp" \
      org.opencontainers.image.url="https://github.com/ly2xxx/md-mcp" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${MD_MCP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

# Run as a non-root user; /data is where markdown gets mounted.
RUN useradd --create-home --uid 10001 mcp && \
    mkdir -p /data && \
    chown -R mcp:mcp /app /data
USER mcp

# Runtime defaults — all overridable at `docker run` / compose time.
ENV MD_FOLDER=/data \
    MD_NAME=markdown-docs \
    MD_TRANSPORT=http \
    MD_HOST=0.0.0.0 \
    MD_PORT=8000 \
    MD_PATH=/mcp

EXPOSE 8000

# Volume for the markdown knowledge base.
VOLUME ["/data"]

# Transport-aware health check: probe the TCP port for HTTP transports; pass
# automatically in stdio mode (no listening port there). See docker/healthcheck.py.
COPY docker/healthcheck.py ./healthcheck.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

ENTRYPOINT ["python", "/app/entrypoint.py"]
