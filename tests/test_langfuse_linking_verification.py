import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sdaa.src.utils.prompt_manager import PromptManager
from sdaa.src.utils.instrumented_gemini import InstrumentedGemini
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest
import os

# Mock Langfuse PromptClient
class MockPromptClient:
    def __init__(self, name, version):
        self.name = name
        self.version = version

    def compile(self, **kwargs):
        return f"Compiled prompt {self.name} v{self.version}"

@pytest.fixture
def mock_langfuse():
    with patch("sdaa.src.utils.prompt_manager.Langfuse") as mock:
        client_instance = mock.return_value
        prompt_client = MockPromptClient("test-prompt", 1)
        client_instance.get_prompt.return_value = prompt_client
        yield mock

@pytest.fixture
def prompt_manager_instance(mock_langfuse):
    # Reset singleton
    PromptManager._instance = None
    pm = PromptManager()
    return pm

def test_get_prompt_object(prompt_manager_instance):
    with patch.dict("os.environ", {"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}):
        # Force re-init with keys
        PromptManager._instance = None
        pm = PromptManager()

        obj = pm.get_prompt_object("test-prompt")
        assert obj is not None
        assert obj.name == "test-prompt"
        assert obj.version == 1

@pytest.mark.asyncio
async def test_instrumented_gemini_linking():
    # Mock opentelemetry trace
    with patch("sdaa.src.utils.instrumented_gemini.trace") as mock_trace:
        tracer = MagicMock()
        mock_trace.get_tracer.return_value = tracer
        span = MagicMock()
        tracer.start_as_current_span.return_value.__enter__.return_value = span

        # Instantiate model
        model = InstrumentedGemini(model="gemini-test")

        # Set prompt
        prompt_obj = MockPromptClient("gemini-prompt", 2)
        model.set_langfuse_prompt(prompt_obj)

        # Mock super().generate_content_async
        async def mock_gen(*args, **kwargs):
            yield "mock-response"

        with patch("google.adk.models.Gemini.generate_content_async", side_effect=mock_gen):
            # Call generate_content_async
            request = LlmRequest(contents=[])
            async for _ in model.generate_content_async(request):
                pass

            # Verify span attributes
            calls = span.set_attribute.call_args_list
            assert any(call[0][0] == "langfuse.observation.prompt.name" and call[0][1] == "gemini-prompt" for call in calls)
            assert any(call[0][0] == "langfuse.observation.prompt.version" and call[0][1] == 2 for call in calls)

@pytest.mark.asyncio
async def test_openrouter_model_linking():
    # Mock opentelemetry trace
    with patch("sdaa.src.utils.openrouter_model.trace") as mock_trace:
        tracer = MagicMock()
        mock_trace.get_tracer.return_value = tracer
        span = MagicMock()
        tracer.start_as_current_span.return_value.__enter__.return_value = span

        # Use real OpenRouterModel instantiation (which creates real AsyncOpenAI)
        # We need to make sure we don't actually hit the network
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy"}):
             model = OpenRouterModel(model_name="openrouter-test", api_key="dummy")

             # Set prompt
             prompt_obj = MockPromptClient("openrouter-prompt", 3)
             model.set_langfuse_prompt(prompt_obj)

             # Mock client.chat.completions.create
             model.client.chat.completions.create = AsyncMock()
             mock_response = MagicMock()
             mock_response.choices = [MagicMock()]
             mock_response.choices[0].message.content = "response"
             mock_response.choices[0].message.tool_calls = None
             model.client.chat.completions.create.return_value = mock_response

             # Call generate_content_async
             # We need to mock request contents properly to avoid errors in OpenRouterModel logic
             from google.genai import types
             request = LlmRequest(contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])])

             async for _ in model.generate_content_async(request):
                 pass

             # Verify span attributes
             calls = span.set_attribute.call_args_list
             assert any(call[0][0] == "langfuse.observation.prompt.name" and call[0][1] == "openrouter-prompt" for call in calls)
             assert any(call[0][0] == "langfuse.observation.prompt.version" and call[0][1] == 3 for call in calls)
