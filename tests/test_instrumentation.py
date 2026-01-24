import os
import unittest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from sdaa.src.core.instrumentation import setup_instrumentation, TaggingSpanProcessor
from langfuse import LangfuseOtelSpanAttributes

class TestInstrumentation(unittest.TestCase):
    @patch('sdaa.src.core.instrumentation.OTLPSpanExporter')
    @patch('sdaa.src.core.instrumentation.GoogleADKInstrumentor')
    @patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
        "LANGFUSE_SECRET_KEY": "sk-lf-test",
        "LANGFUSE_HOST": "http://localhost:3000"
    })
    def test_setup_instrumentation(self, MockGoogleADK, MockExporter):
        # Reset trace provider to avoid conflict with other tests if run in suite
        trace.set_tracer_provider(None)

        setup_instrumentation()

        # Check Exporter initialization
        MockExporter.assert_called_once()
        call_args = MockExporter.call_args
        self.assertEqual(call_args.kwargs['endpoint'], "http://localhost:3000/api/public/otlp/v1/traces")
        self.assertIn("Authorization", call_args.kwargs['headers'])
        self.assertTrue(call_args.kwargs['headers']['Authorization'].startswith("Basic "))

        # Check GoogleADK instrumentation
        MockGoogleADK.return_value.instrument.assert_called_once()

    def test_tagging_span_processor(self):
        processor = TaggingSpanProcessor()
        mock_span = MagicMock()

        # Test root span (parent_context is None)
        processor.on_start(mock_span, None)
        mock_span.set_attribute.assert_called_with(LangfuseOtelSpanAttributes.TRACE_TAGS, ["ADK-DocsDiver"])

        mock_span.reset_mock()

        # Test child span (valid parent context)
        with patch('opentelemetry.trace.get_current_span') as mock_get_span:
            # Case 1: Parent is INVALID_SPAN (should be treated as root)
            mock_get_span.return_value = trace.INVALID_SPAN
            # Context can be anything since we mock get_current_span
            processor.on_start(mock_span, "some_context")
            mock_span.set_attribute.assert_called_with(LangfuseOtelSpanAttributes.TRACE_TAGS, ["ADK-DocsDiver"])

            mock_span.reset_mock()

            # Case 2: Parent is a valid span (should NOT add tag)
            mock_get_span.return_value = MagicMock()
            processor.on_start(mock_span, "some_context")
            mock_span.set_attribute.assert_not_called()

if __name__ == '__main__':
    unittest.main()
