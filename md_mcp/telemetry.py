"""Optional OpenTelemetry instrumentation for md-mcp.

Design goals
------------
1. **Optional.** The OTEL packages live behind the ``observability`` extra
   (``pip install md-mcp[observability]``). If they are missing, or the
   collector is unreachable, every public function degrades to a no-op — the
   MCP server must never fail because telemetry is unavailable.
2. **stdio-safe.** Claude Desktop spawns a fresh ``docker run --rm`` container
   per session, so the process can exit at any time. We register an ``atexit``
   flush so the BatchSpanProcessor does not silently drop the session's spans.
3. **Privacy-aware.** Tool arguments (search queries) can contain note
   content. By default only the *shape* of a call is recorded (tool name,
   argument keys, result size, duration, status). Set
   ``MD_OTEL_RECORD_ARGUMENTS=true`` to record argument values.

Environment variables
---------------------
    OTEL_EXPORTER_OTLP_ENDPOINT  OTLP gRPC collector endpoint. REQUIRED to
                                 activate telemetry - unset means telemetry off.
    OTEL_SERVICE_NAME            Service name in traces/metrics (default: md-mcp)
    OTEL_SDK_DISABLED            "true" turns everything off
    MD_OTEL_RECORD_ARGUMENTS     "true" records tool argument values (default: false)
"""

from __future__ import annotations

import atexit
import os
import sys
import time

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "md-mcp")
# Telemetry is opt-in per process: it only activates when a collector endpoint
# is explicitly configured. This lets the OTEL packages ship in the default
# image without producing export-retry noise for users who don't run a collector.
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
DISABLED = os.getenv("OTEL_SDK_DISABLED", "false").lower() in ("1", "true", "yes")
RECORD_ARGUMENTS = os.getenv("MD_OTEL_RECORD_ARGUMENTS", "false").lower() in (
    "1",
    "true",
    "yes",
)

# Module-level singletons, populated once by init_telemetry().
_initialized = False
_tracer = None
_tool_counter = None
_tool_duration = None


def _log(msg: str) -> None:
    # stderr only: stdout carries the JSON-RPC stream in stdio transport.
    sys.stderr.write(f"[md-mcp telemetry] {msg}\n")
    sys.stderr.flush()


def init_telemetry() -> bool:
    """Initialise OTEL once per process. Returns True if telemetry is active."""
    global _initialized, _tracer, _tool_counter, _tool_duration

    if _initialized:
        return True
    if DISABLED:
        _log("OTEL_SDK_DISABLED is set - telemetry off.")
        return False
    if not OTLP_ENDPOINT:
        # Silent: this is the normal state for users without a collector.
        return False

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        _log(
            "OpenTelemetry packages not installed - running without telemetry. "
            "Install with: pip install md-mcp[observability]"
        )
        return False

    try:
        resource = Resource.create(
            {
                "service.name": SERVICE_NAME,
                "service.namespace": "mcp",
                "deployment.environment": os.getenv("DEPLOY_ENV", "local"),
            }
        )

        trace_provider = TracerProvider(resource=resource)
        trace_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))
        )
        trace.set_tracer_provider(trace_provider)
        _tracer = trace.get_tracer(SERVICE_NAME)

        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True),
            export_interval_millis=int(
                os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "10000")
            ),
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)

        meter = metrics.get_meter(SERVICE_NAME)
        _tool_counter = meter.create_counter(
            "mcp.tool.calls",
            unit="1",
            description="Total MCP tool invocations.",
        )
        _tool_duration = meter.create_histogram(
            "mcp.tool.duration",
            unit="s",
            description="MCP tool call latency.",
        )

        # stdio containers are short-lived (`docker run --rm` per Claude
        # session): flush both pipelines on interpreter exit or the batch
        # processors drop everything recorded in the final export window.
        def _shutdown() -> None:
            try:
                trace_provider.shutdown()
                meter_provider.shutdown()
            except Exception:
                pass

        atexit.register(_shutdown)

        _initialized = True
        _log(f"OTEL active -> {OTLP_ENDPOINT} (service={SERVICE_NAME})")
        return True
    except Exception as exc:  # pragma: no cover - defensive
        _log(f"init failed, running without telemetry: {exc}")
        return False


def create_tracing_middleware():
    """Return a FastMCP middleware that traces every MCP request, or None.

    Import of fastmcp middleware types is deferred so this module stays
    importable in minimal environments.
    """
    if not _initialized:
        return None

    from fastmcp.server.middleware import Middleware, MiddlewareContext

    tracer = _tracer
    tool_counter = _tool_counter
    tool_duration = _tool_duration

    class OtelMiddleware(Middleware):
        """Spans + metrics for tool calls; spans only for other MCP requests."""

        async def on_call_tool(self, context: MiddlewareContext, call_next):
            tool_name = getattr(context.message, "name", "unknown")
            arguments = getattr(context.message, "arguments", None) or {}

            with tracer.start_as_current_span(f"mcp.tool/{tool_name}") as span:
                span.set_attribute("mcp.tool.name", tool_name)
                span.set_attribute("mcp.method", context.method or "tools/call")
                # Privacy default: record which arguments were passed, not
                # their values (queries can contain note content).
                span.set_attribute("mcp.tool.argument_keys", sorted(arguments))
                if RECORD_ARGUMENTS:
                    for key, value in arguments.items():
                        span.set_attribute(f"mcp.tool.arguments.{key}", str(value)[:500])

                status = "ok"
                start = time.perf_counter()
                try:
                    result = await call_next(context)
                except Exception as exc:
                    status = "error"
                    span.record_exception(exc)
                    from opentelemetry.trace import StatusCode

                    span.set_status(StatusCode.ERROR, str(exc))
                    raise
                finally:
                    duration = time.perf_counter() - start
                    attrs = {"tool": tool_name, "status": status}
                    tool_counter.add(1, attrs)
                    tool_duration.record(duration, attrs)

                content = getattr(result, "content", None)
                if content is not None:
                    span.set_attribute("mcp.tool.result_blocks", len(content))
                return result

        async def on_request(self, context: MiddlewareContext, call_next):
            method = context.method or "unknown"
            if method == "tools/call":
                # Handled with richer attributes by on_call_tool.
                return await call_next(context)
            with tracer.start_as_current_span(f"mcp.request/{method}") as span:
                span.set_attribute("mcp.method", method)
                return await call_next(context)

    return OtelMiddleware()
