import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import os
from openai import AsyncOpenAI
from sdaa.src.utils.prompt_manager import PromptManager
from sdaa.src.utils.openrouter_model import OpenRouterModel
from sdaa.src.utils.instrumented_gemini import InstrumentedGemini
from google.adk.models import LlmRequest
from google.genai import types

class TestLangfuseLinking(unittest.TestCase):
    def setUp(self):
        self.mock_langfuse = MagicMock()
        self.mock_prompt = MagicMock()
        self.mock_prompt.name = "test-prompt"
        self.mock_prompt.version = 1
        self.mock_prompt.compile.return_value = "Compiled Prompt"
        self.mock_langfuse.get_prompt.return_value = self.mock_prompt

        # Patch PromptManager to use mock client
        self.prompt_manager_patcher = patch("sdaa.src.utils.prompt_manager.Langfuse", return_value=self.mock_langfuse)
        self.MockLangfuseClass = self.prompt_manager_patcher.start()

        # Reset singleton and client
        PromptManager._instance = None
        self.prompt_manager = PromptManager()
        self.prompt_manager._client = self.mock_langfuse

    def tearDown(self):
        self.prompt_manager_patcher.stop()

    @patch("sdaa.src.utils.openrouter_model.trace")
    # We don't patch AsyncOpenAI class, we construct a real one with dummy key and mock the method on the instance
    def test_openrouter_linking(self, mock_trace):
        # Setup mocks
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_trace.get_current_span.return_value = mock_span

        # Create real client but mock the method
        client = AsyncOpenAI(api_key="dummy")
        client.chat.completions.create = AsyncMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="Test Response", tool_calls=None))
        ]

        # We need to inject this client into OpenRouterModel.
        # OpenRouterModel creates client in __init__.
        # We can pass api_key="dummy" to OpenRouterModel, then replace self.client?
        # Or patch AsyncOpenAI in the module to return our client.

        with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=client):
            model = OpenRouterModel(model_name="test-model", api_key="dummy")

        # Re-apply the mock to the instance method because OpenRouterModel uses the client instance
        model.client.chat.completions.create = client.chat.completions.create

        prompt_obj = self.prompt_manager.get_prompt_object("test-prompt")
        model.set_langfuse_prompt(prompt_obj)

        request = LlmRequest(contents=[types.Content(parts=[types.Part.from_text(text="User input")], role="user")])

        async def run():
            async for _ in model.generate_content_async(request):
                pass

        asyncio.run(run())

        # Verify
        mock_trace.get_current_span.assert_called()
        self.assertTrue(mock_span.set_attribute.called)

        calls = mock_span.set_attribute.call_args_list
        found_name = False
        found_version = False
        for call in calls:
            args = call[0]
            if "prompt.name" in args[0] and args[1] == "test-prompt":
                found_name = True
            if "prompt.version" in args[0] and args[1] == 1:
                found_version = True

        self.assertTrue(found_name, "Prompt name attribute not set on span")
        self.assertTrue(found_version, "Prompt version attribute not set on span")

    @patch("sdaa.src.utils.instrumented_gemini.trace")
    @patch("google.adk.models.Gemini.generate_content_async")
    def test_gemini_linking(self, mock_super_generate, mock_trace):
        # Setup mocks
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_trace.get_current_span.return_value = mock_span

        async def mock_gen(*args, **kwargs):
            yield "chunk"
        mock_super_generate.side_effect = mock_gen

        # Fix: Pass model as keyword argument
        model = InstrumentedGemini(model="test-model")

        prompt_obj = self.prompt_manager.get_prompt_object("test-prompt")
        model.set_langfuse_prompt(prompt_obj)

        request = LlmRequest(contents=[types.Content(parts=[types.Part.from_text(text="User input")], role="user")])

        async def run():
            async for _ in model.generate_content_async(request):
                pass

        asyncio.run(run())

        # Verify
        mock_trace.get_current_span.assert_called()

        calls = mock_span.set_attribute.call_args_list
        found_name = False
        found_version = False
        for call in calls:
            args = call[0]
            if "prompt.name" in args[0] and args[1] == "test-prompt":
                found_name = True
            if "prompt.version" in args[0] and args[1] == 1:
                found_version = True

        self.assertTrue(found_name, "Prompt name attribute not set on span")
        self.assertTrue(found_version, "Prompt version attribute not set on span")

if __name__ == '__main__':
    unittest.main()
