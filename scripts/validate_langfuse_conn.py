import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from opentelemetry import trace
from sdaa.src.core.instrumentation import setup_instrumentation, run_observation

setup_instrumentation()
tracer = trace.get_tracer(__name__)

with run_observation("connectivity-check", {"purpose": "connectivity check"}) as root:
    with tracer.start_as_current_span("docsdiver-test-span"):
        print("Started docsdiver-test-span")
    if root is not None:
        root.update(output={"status": "test completed"})

print("Flushed. Inspect the docsdiver.run trace in session connectivity-check; this does not verify backend delivery.")
