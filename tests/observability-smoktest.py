from src.observability import setup_observability, run_trace, PROJECT_TAG
from opentelemetry import trace

setup_observability()

with run_trace(tags=[PROJECT_TAG]):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("docsdiver.test_span"):
        pass

trace.get_tracer_provider().force_flush()
print("flushed")