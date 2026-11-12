import json
import uuid

import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sdaa.src.core import instrumentation


@pytest.mark.parametrize("fails", [False, True])
def test_run_hierarchy_propagation_and_flush(monkeypatch, fails):
    provider = TracerProvider()
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "test")
    monkeypatch.setenv("LANGFUSE_RELEASE", "test-release")
    provider.add_span_processor(instrumentation.TaggingSpanProcessor())
    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-test-" + uuid.uuid4().hex, secret_key="sk-test",
        base_url="http://localhost:1", tracer_provider=provider,
        span_exporter=exporter, should_export_span=lambda span: True,
        environment="test", release="test-release",
    )
    monkeypatch.setattr(instrumentation, "_langfuse_client", client)
    tracer = provider.get_tracer("docsdiver-test")

    def run():
        with instrumentation.run_observation("run-test", {"query": "audit"}) as root:
            with tracer.start_as_current_span("generation") as child:
                child.set_attribute("langfuse.observation.type", "generation")
                child.set_attribute("langfuse.observation.cost_details", '{"total":0.01}')
            if fails:
                raise SystemExit(1)
            root.update(output={"report": "findings"})

    try:
        if fails:
            with pytest.raises(SystemExit):
                run()
        else:
            run()
        # run_observation flushes without sleeping or a process-exit hook.
        spans = exporter.get_finished_spans()
        assert len(spans) == 2
        root = next(s for s in spans if s.name == "docsdiver.run")
        child = next(s for s in spans if s.name == "generation")
        assert child.parent.span_id == root.context.span_id
        assert child.context.trace_id == root.context.trace_id
        for span in spans:
            assert span.attributes["session.id"] == "run-test"
            assert span.attributes["user.id"] == "user_001"
            assert "ADK-DocsDiver" in span.attributes["langfuse.trace.tags"]
            assert span.attributes["langfuse.environment"] == "test"
            assert span.attributes["langfuse.release"] == "test-release"
        assert json.loads(root.attributes["langfuse.observation.input"]) == {"query": "audit"}
        output = json.loads(root.attributes["langfuse.observation.output"])
        assert output == ({"status": "failed"} if fails else {"report": "findings"})
    finally:
        client.shutdown()
        provider.shutdown()


def test_prompt_only_client_has_no_exporter(monkeypatch):
    from unittest.mock import Mock
    constructor = Mock()
    monkeypatch.setattr(instrumentation, "_langfuse_client", None)
    monkeypatch.setattr(instrumentation, "Langfuse", constructor)
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000/")
    instrumentation.get_langfuse_client()
    constructor.assert_called_once_with(base_url="http://localhost:3000", tracing_enabled=False)
