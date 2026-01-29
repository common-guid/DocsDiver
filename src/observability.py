from __future__ import annotations

import base64
import os
from contextlib import contextmanager
from typing import Iterator, Sequence

import openlit
from dotenv import load_dotenv
from opentelemetry import trace

PROJECT_TAG = "crewai_docsdiver"

_LANGSMITH_PROCESSOR_ADDED = False


def _langfuse_otlp_endpoint() -> str | None:
    """Return the OTLP *base* endpoint for Langfuse.

    Note: OpenLit sets OTEL_EXPORTER_OTLP_ENDPOINT, and the OTLP HTTP exporter will
    append '/v1/traces' automatically. So we must *not* include '/v1/traces' here.

    We accept either:
    - base endpoint:   http(s)://<host>/api/public/otel
    - traces endpoint: http(s)://<host>/api/public/otel/v1/traces (we normalize it)
    """

    endpoint = os.getenv("LANGFUSE_OTEL_TRACES_ENDPOINT", "").strip()
    if endpoint:
        for suffix in ("/v1/traces", "/v1/traces/"):
            if endpoint.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                break
        return endpoint.rstrip("/")

    base_url = os.getenv("LANGFUSE_BASE_URL", "").strip()
    if base_url:
        return f"{base_url.rstrip('/')}/api/public/otel"

    return None


def _langfuse_headers() -> str | None:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    if not (public_key and secret_key):
        return None
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("utf-8")
    return f"Authorization=Basic {auth}"


def setup_observability() -> None:
    global _LANGSMITH_PROCESSOR_ADDED

    load_dotenv()

    os.environ.setdefault("OTEL_SERVICE_NAME", PROJECT_TAG)
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

    langfuse_endpoint = _langfuse_otlp_endpoint()
    langfuse_headers = _langfuse_headers()

    if langfuse_endpoint and langfuse_headers:
        openlit.init(
            service_name=PROJECT_TAG,
            otlp_endpoint=langfuse_endpoint,
            otlp_headers=langfuse_headers,
        )
    else:
        openlit.init(service_name=PROJECT_TAG)

    # Add LangSmith alongside the OpenLit-configured exporter (Langfuse).
    if _LANGSMITH_PROCESSOR_ADDED:
        return

    langsmith_api_key = os.getenv("LANGSMITH_API_KEY", "").strip()
    if not langsmith_api_key:
        return

    langsmith_base = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").strip()
    langsmith_project = os.getenv("LANGSMITH_PROJECT", "").strip() or PROJECT_TAG

    try:
        from langsmith.integrations.otel.processor import OtelSpanProcessor
    except Exception:
        return

    trace.get_tracer_provider().add_span_processor(
        OtelSpanProcessor(api_key=langsmith_api_key, project=langsmith_project, url=langsmith_base)
    )
    _LANGSMITH_PROCESSOR_ADDED = True


@contextmanager
def run_trace(name: str = "docsdiver.run", tags: Sequence[str] | None = None) -> Iterator[None]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if tags:
            span.set_attribute("langfuse.trace.tags", list(tags))
        yield
