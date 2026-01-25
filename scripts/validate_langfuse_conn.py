import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from opentelemetry import trace
from sdaa.src.core.instrumentation import setup_instrumentation

setup_instrumentation()
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("docsdiver-test-span"):
    print("Started docsdiver-test-span")

# Give BatchSpanProcessor time to flush before exit
print("Sleeping to allow exporter flush...")
time.sleep(5)
print("Done. If Langfuse is configured correctly, you should see a trace named 'docsdiver-test-span' tagged with 'ADK-DocsDiver'.")
