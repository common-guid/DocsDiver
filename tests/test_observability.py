import pytest
import asyncio
import os
from typing import Optional
from unittest.mock import MagicMock, patch, AsyncMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.utils.instrumented_gemini import InstrumentedGemini
from google.adk.models import LlmRequest, Gemini
from google.genai import types
from openai import AsyncOpenAI

# Setup Tracer for tests
@pytest.fixture
def memory_exporter():
    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()

    # Check if we can add processor to current provider
    if not hasattr(provider, "add_span_processor"):
        # If it's a proxy or invalid, try setting a new one (might warn/fail if already set but not capable)
        # But commonly in tests if no setup happened, it's a Proxy. set_tracer_provider replaces it.
        # If setup happened, it's a TracerProvider.
        provider = TracerProvider()
        try:
            trace.set_tracer_provider(provider)
        except Exception:
            pass # Ignore if already set

    # Re-fetch in case set_tracer_provider was ignored
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(SimpleSpanProcessor(exporter))

    return exporter

@pytest.fixture
def mock_langfuse_prompt():
    prompt = MagicMock()
    prompt.name = "test-prompt"
    prompt.version = 1
    return prompt

@pytest.mark.asyncio
async def test_openrouter_linking(memory_exporter, mock_langfuse_prompt):
    # Use real AsyncOpenAI but patch the API call to avoid network
    # We set a dummy API key to pass validation
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy"}):
        model = OpenRouterModel("test-model", api_key="dummy")

    model.set_langfuse_prompt(mock_langfuse_prompt)

    # Patch the chat.completions.create method on the client instance
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="test response", tool_calls=None))]

    # The client is AsyncOpenAI. chat.completions.create is an async method.
    model.client.chat.completions.create = AsyncMock(return_value=mock_response)

    request = LlmRequest(contents=[types.Content(parts=[types.Part.from_text(text="hi")], role="user")])

    async for _ in model.generate_content_async(request):
        pass

    spans = memory_exporter.get_finished_spans()
    assert len(spans) >= 1
    # Find the OpenRouter span
    or_span = next((s for s in spans if s.name == "OpenRouter.generate_content"), None)
    assert or_span is not None
    # Langfuse SDK uses 'langfuse.observation.prompt.name'
    key_name = "langfuse.observation.prompt.name"
    key_version = "langfuse.observation.prompt.version"

    # Check for either key to be robust across SDK versions (or fallback)
    name = or_span.attributes.get(key_name) or or_span.attributes.get("langfuse.prompt.name")
    version = or_span.attributes.get(key_version) or or_span.attributes.get("langfuse.prompt.version")

    assert name == "test-prompt"
    assert version == 1

@pytest.mark.asyncio
async def test_gemini_linking(memory_exporter, mock_langfuse_prompt):
    # Mock Gemini parent behavior
    with patch("google.adk.models.Gemini.generate_content_async", new_callable=MagicMock) as mock_super:
        # Define an async generator for the mock return value
        async def async_gen(*args, **kwargs):
            yield types.Part.from_text(text="gemini chunk")

        mock_super.side_effect = async_gen

        # We need a client for Gemini init. Pydantic might validate it.
        # google.adk.models.Gemini expects 'client'.
        # If we pass None, it might try to create one.
        # Let's pass a MagicMock and hope BaseLlm doesn't strict check it,
        # OR BaseLlm is not checking Gemini client specifically?
        # Actually InstrumentedGemini inherits Gemini -> GoogleLLM -> BaseLlm.
        # GoogleLLM defines client: GoogleGenAIClient.
        # So we probably need to patch the validation or pass a real client?
        # Let's try passing a MagicMock. If it fails like OpenRouter, we'll need a real client.
        # But GoogleGenAIClient is harder to instantiate without creds.

        # However, checking sdaa/src/utils/instrumented_gemini.py...
        # It inherits Gemini.
        # Let's see if we can get away with a mock if we patch Pydantic validation? No.
        # But maybe GoogleLLM uses 'Any' or not strictly validated field?
        # Let's try running it. If it fails, we will see.

        mock_client = MagicMock()
        try:
             model = InstrumentedGemini(model="gemini-pro", client=mock_client)
        except Exception:
             # If validation fails, try to bypass init or use a real client with dummy creds?
             # Or just patch 'google.adk.models.Gemini' __init__?
             pass

        # Actually, let's just patch the Pydantic validation for the test?
        # Too complex.
        # Let's hope GoogleLLM doesn't validate 'client' strictly or MagicMock passes.

        # Re-instantiate to be sure
        model = InstrumentedGemini(model="gemini-pro", client=mock_client)
        model.set_langfuse_prompt(mock_langfuse_prompt)

        request = LlmRequest(contents=[types.Content(parts=[types.Part.from_text(text="hi")], role="user")])

        async for _ in model.generate_content_async(request):
            pass

    spans = memory_exporter.get_finished_spans()

    assert len(spans) >= 1
    # Find the Gemini span
    gemini_span = next((s for s in spans if s.name == "Gemini.generate_content"), None)
    assert gemini_span is not None

    key_name = "langfuse.observation.prompt.name"
    key_version = "langfuse.observation.prompt.version"

    name = gemini_span.attributes.get(key_name) or gemini_span.attributes.get("langfuse.prompt.name")
    version = gemini_span.attributes.get(key_version) or gemini_span.attributes.get("langfuse.prompt.version")

    assert name == "test-prompt"
    assert version == 1

def test_langsmith_exporter_setup():
    # Test that setup_instrumentation configures LangSmith if env var is set
    with patch.dict("os.environ", {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": "test-project"}):
        with patch("sdaa.src.core.instrumentation.configure_langsmith") as mock_configure:
             # We also mock GoogleADKInstrumentor to avoid actual instrumentation during this unit test
             with patch("sdaa.src.core.instrumentation.GoogleADKInstrumentor"):
                 from sdaa.src.core.instrumentation import setup_instrumentation
                 setup_instrumentation()
                 mock_configure.assert_called_once_with(project_name="test-project")
