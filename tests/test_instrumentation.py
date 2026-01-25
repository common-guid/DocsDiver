import os
import unittest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from sdaa.src.core.instrumentation import setup_instrumentation, TaggingSpanProcessor, LangfuseOtelSpanAttributes, LANGFUSE_AVAILABLE

class TestInstrumentation(unittest.TestCase):
    @patch('sdaa.src.core.instrumentation.requests.get')
    @patch('sdaa.src.core.instrumentation.OTLPSpanExporter')
    @patch('sdaa.src.core.instrumentation.GoogleADKInstrumentor')
    @patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
        "LANGFUSE_SECRET_KEY": "sk-lf-test",
        "LANGFUSE_HOST": "http://localhost:3000"
    }, clear=True)
    def test_setup_instrumentation(self, MockGoogleADK, MockExporter, MockRequestsGet):
        # Reset trace provider to avoid conflict with other tests if run in suite
        trace.set_tracer_provider(None)

        # Simulate reachable Langfuse host so exporter is configured
        MockRequestsGet.return_value.status_code = 200

        setup_instrumentation()

        if LANGFUSE_AVAILABLE:
            # Check Exporter initialization for Langfuse (should be called once given env vars)
            # Note: Depending on logic, if only Langfuse vars are set, it's called once.
            self.assertEqual(MockExporter.call_count, 1)
            call_args = MockExporter.call_args
            self.assertEqual(call_args.kwargs['endpoint'], "http://localhost:3000/api/public/otel/v1/traces")
            self.assertIn("Authorization", call_args.kwargs['headers'])
            self.assertTrue(call_args.kwargs['headers']['Authorization'].startswith("Basic "))
        else:
            # If Langfuse is not available (e.g. Python 3.14 issue), it should skipped with a warning
            self.assertEqual(MockExporter.call_count, 0)

        # Check GoogleADK instrumentation (should happen regardless of Langfuse status, if has_exporter is True)
        # Wait, has_exporter logic: if Langfuse fails, has_exporter is False (unless LangSmith is also set).
        # In this test, only Langfuse vars are set. So if LANGFUSE_AVAILABLE is False, has_exporter is False.
        if LANGFUSE_AVAILABLE:
            MockGoogleADK.return_value.instrument.assert_called_once()
        else:
            MockGoogleADK.return_value.instrument.assert_not_called()

    @patch('sdaa.src.core.instrumentation.OTLPSpanExporter')
    @patch('sdaa.src.core.instrumentation.GoogleADKInstrumentor')
    @patch.dict(os.environ, {
        "LANGSMITH_API_KEY": "ls_test_key",
        "LANGSMITH_PROJECT": "ls_test_project",
        "LANGSMITH_ENDPOINT": "https://api.test.com"
    })
    def test_setup_instrumentation_langsmith(self, MockGoogleADK, MockExporter):
        # Clear Langfuse vars for this test to isolate LangSmith
        with patch.dict(os.environ, {}, clear=True):
             os.environ["LANGSMITH_API_KEY"] = "ls_test_key"
             os.environ["LANGSMITH_PROJECT"] = "ls_test_project"
             os.environ["LANGSMITH_ENDPOINT"] = "https://api.test.com"

             trace.set_tracer_provider(None)
             setup_instrumentation()

             self.assertEqual(MockExporter.call_count, 1)
             call_args = MockExporter.call_args
             self.assertEqual(call_args.kwargs['endpoint'], "https://api.test.com/otel/v1/traces")
             self.assertEqual(call_args.kwargs['headers']['x-api-key'], "ls_test_key")
             self.assertEqual(call_args.kwargs['headers']['x-langsmith-project'], "ls_test_project")

    def test_tagging_span_processor(self):
        processor = TaggingSpanProcessor()
        mock_span = MagicMock()

        # Test root span (parent_context is None)
        processor.on_start(mock_span, None)

        # Check both calls were made
        expected_calls = [
            unittest.mock.call(LangfuseOtelSpanAttributes.TRACE_TAGS, ["ADK-DocsDiver"]),
            unittest.mock.call("langsmith.span.tags", ["ADK-DocsDiver"])
        ]
        mock_span.set_attribute.assert_has_calls(expected_calls, any_order=True)

        mock_span.reset_mock()

        # Test child span (valid parent context)
        with patch('opentelemetry.trace.get_current_span') as mock_get_span:
            # Case 1: Parent is INVALID_SPAN (should be treated as root)
            mock_get_span.return_value = trace.INVALID_SPAN
            # Context can be anything since we mock get_current_span
            processor.on_start(mock_span, "some_context")
            mock_span.set_attribute.assert_has_calls(expected_calls, any_order=True)

            mock_span.reset_mock()

            # Case 2: Parent is a valid span (should NOT add tag)
            mock_get_span.return_value = MagicMock()
            processor.on_start(mock_span, "some_context")
            mock_span.set_attribute.assert_not_called()

    @patch('sdaa.src.core.instrumentation.LANGFUSE_AVAILABLE', False)
    @patch('sdaa.src.core.instrumentation.OTLPSpanExporter')
    @patch('sdaa.src.core.instrumentation.GoogleADKInstrumentor')
    @patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
        "LANGFUSE_SECRET_KEY": "sk-lf-test"
    }, clear=True)
    def test_setup_instrumentation_langfuse_unavailable(self, MockGoogleADK, MockExporter):
        # Reset trace provider
        trace.set_tracer_provider(None)

        with patch('builtins.print') as mock_print:
            setup_instrumentation()

            # Should check for warning message
            found_warning = False
            for call in mock_print.call_args_list:
                if "likely due to Python 3.14 incompatibility" in str(call):
                    found_warning = True
                    break
            self.assertTrue(found_warning, "Should print warning when Langfuse is unavailable")

        # Should not initialize exporter
        MockExporter.assert_not_called()

if __name__ == '__main__':
    unittest.main()
