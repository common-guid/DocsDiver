import os
import base64
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from langfuse import LangfuseOtelSpanAttributes

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

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        pass

def setup_instrumentation():
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        print("Warning: LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set. Observability disabled.")
        return

    # Ensure host doesn't have trailing slash
    if host.endswith("/"):
        host = host[:-1]

    endpoint = f"{host}/api/public/otlp/v1/traces"

    # Basic Auth Header
    credentials = f"{public_key}:{secret_key}"
    auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"

    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers={"Authorization": auth_header}
    )

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    provider.add_span_processor(TaggingSpanProcessor())

    trace.set_tracer_provider(provider)

    # Initialize Google ADK Instrumentation
    # This will auto-instrument the Google ADK classes to emit traces
    GoogleADKInstrumentor().instrument()
    print(f"Langfuse observability initialized at {host}")
