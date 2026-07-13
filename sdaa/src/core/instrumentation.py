import os
import base64
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from langsmith.integrations.otel import configure as configure_langsmith
import requests

try:
    from langfuse import LangfuseOtelSpanAttributes
    LANGFUSE_AVAILABLE = True
except Exception:
    # Handle Python 3.14 + Pydantic v1 incompatibility or missing library
    class LangfuseOtelSpanAttributes:
        TRACE_TAGS = "langfuse.trace.tags"
    LANGFUSE_AVAILABLE = False

load_dotenv()


class TaggingSpanProcessor(SpanProcessor):
    def on_start(self, span, parent_context):
        # Check if it is a root span (no parent or parent is invalid)
        is_root = False
        if parent_context is None:
            is_root = True
        else:
            parent_span = trace.get_current_span(parent_context)
            if parent_span is None or parent_span == trace.INVALID_SPAN:
                is_root = True

        if is_root:
            # Add the tag using the Langfuse attribute key
            # Langfuse expects a list of strings
            span.set_attribute(LangfuseOtelSpanAttributes.TRACE_TAGS, ["ADK-DocsDiver"])
            # LangSmith tags (list of strings)
            span.set_attribute("langsmith.span.tags", ["ADK-DocsDiver"])

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        pass


def setup_instrumentation():
    """Configure observability for LangSmith + Google ADK (and optionally Langfuse).

    LangSmith tracing is configured via langsmith.integrations.otel.configure, which sets up
    the OpenTelemetry exporter for LangSmith automatically. Langfuse continues to use a
    manual OTLP exporter attached to the same or a new TracerProvider.
    """
    has_exporter = False

    # --- LangSmith Setup (via official ADK integration) ---
    ls_api_key = os.getenv("LANGSMITH_API_KEY")
    ls_project = os.getenv("LANGSMITH_PROJECT") or "ADK-DocsDiver"

    if ls_api_key:
        try:
            configure_langsmith(project_name=ls_project)
            print(f"LangSmith tracing configured for project {ls_project}")
            has_exporter = True
        except Exception as exc:
            print(f"Warning: LangSmith configure() failed: {exc}")
    else:
        print("LangSmith API key not set. Skipping LangSmith tracing configuration.")

    provider: TracerProvider
    if ls_api_key:
        # LangSmith configure() is expected to install a global TracerProvider.
        current_provider = trace.get_tracer_provider()
        if isinstance(current_provider, TracerProvider):
            provider = current_provider
        else:
            # Fallback: if configure() used a different provider type, create our own for Langfuse.
            provider = TracerProvider()
            trace.set_tracer_provider(provider)
    else:
        # No LangSmith configured; create our own provider for Langfuse / custom tagging
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

    # --- Langfuse Setup ---
    # Prefer LANGFUSE_HOST if set (OTEL endpoint base), otherwise fall back to
    # LANGFUSE_BASE_URL to match existing .env usage, and finally localhost.
    lf_host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000")
    lf_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    lf_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    # Optional explicit override matching Langfuse OTEL docs (e.g. /api/public/otel/v1/traces)
    lf_traces_endpoint = os.getenv("LANGFUSE_OTEL_TRACES_ENDPOINT")

    if lf_public_key and lf_secret_key:
        if not LANGFUSE_AVAILABLE:
            print(
                "Warning: Langfuse credentials found but langfuse library could not be imported "
                "(likely due to Python 3.14 incompatibility). Skipping Langfuse setup."
            )
        else:
            # Ensure host doesn't have trailing slash
            if lf_host.endswith("/"):
                lf_host = lf_host[:-1]

            # Lightweight connectivity check: if Langfuse host is not reachable,
            # skip configuring the exporter to avoid noisy connection errors.
            try:
                # Check health endpoint specifically to ensure service is up
                health_url = f"{lf_host}/api/public/health"
                requests.get(health_url, timeout=1).raise_for_status()
                lf_reachable = True
            except Exception:
                lf_reachable = False

            if not lf_reachable:
                print(f"Langfuse host {lf_host} not reachable; disabling Langfuse observability.")
            else:
                if lf_traces_endpoint:
                    lf_endpoint = lf_traces_endpoint
                else:
                    # Use documented OTEL traces endpoint: /api/public/otel/v1/traces
                    lf_endpoint = f"{lf_host}/api/public/otel/v1/traces"

                # Basic Auth Header
                credentials = f"{lf_public_key}:{lf_secret_key}"
                auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"

                lf_exporter = OTLPSpanExporter(
                    endpoint=lf_endpoint,
                    headers={"Authorization": auth_header}
                )
                provider.add_span_processor(BatchSpanProcessor(lf_exporter))
                has_exporter = True
                print(f"Langfuse observability initialized at {lf_endpoint}")
    else:
        print("Langfuse credentials not found.")

    if has_exporter:
        # Root-span tagging for both LangSmith and Langfuse traces
        provider.add_span_processor(TaggingSpanProcessor())
        trace.set_tracer_provider(provider)

        print("Observability instrumentation complete.")
        return True
    else:
        print("Warning: No observability credentials found. Observability disabled.")
        return False
