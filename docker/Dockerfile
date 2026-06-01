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
ARG INSTALL_SEMANTIC=false
RUN pip install --upgrade pip && \
    if [ "$INSTALL_SEMANTIC" = "true" ]; then \
        pip install ".[semantic]"; \
    else \
        pip install .; \
    fi

# Container entrypoint (HTTP-by-default runner).
COPY docker/entrypoint.py ./entrypoint.py

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

# Health check for HTTP transports: confirm the port is accepting connections.
# (No-op usefulness in stdio mode — there is no listening port then.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket, os, sys; s=socket.socket(); s.settimeout(3); sys.exit(0 if s.connect_ex(('127.0.0.1', int(os.environ.get('MD_PORT','8000'))))==0 else 1)"

ENTRYPOINT ["python", "/app/entrypoint.py"]
