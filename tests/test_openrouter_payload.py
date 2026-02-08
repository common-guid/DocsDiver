
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from google.adk.models import LlmRequest
from google.genai import types

class TestOpenRouterPayload(unittest.TestCase):
    def test_assistant_message_content_is_empty_string(self):
        # Patch openai module globally only for this test block
        mock_openai = MagicMock()
        mock_openai.AsyncOpenAI = MagicMock()

        with patch.dict(sys.modules, {"openai": mock_openai}):
            # We need to ensure sdaa.src.utils.openrouter_model is re-imported to pick up the mock
            if "sdaa.src.utils.openrouter_model" in sys.modules:
                del sys.modules["sdaa.src.utils.openrouter_model"]

            from sdaa.src.utils.openrouter_model import OpenRouterModel

            # Setup mock client
            mock_client_instance = AsyncMock()
            mock_client_instance.chat.completions.create.return_value = AsyncMock()

            # OpenRouterModel uses AsyncOpenAI() to create client
            # So mock_openai.AsyncOpenAI() should return our mock_client_instance
            mock_openai.AsyncOpenAI.return_value = mock_client_instance

            # Instantiate model
            # Pydantic validation should pass because the type hint AsyncOpenAI is now the mock class
            model = OpenRouterModel(model_name="x-ai/grok-4.1-fast", api_key="dummy")

            # Create a request with tool call
            contents = []
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Audit permissions")]))

            # Assistant message with tool call
            try:
                fc = types.FunctionCall(name="report_permissions_matrix", args={"findings": "Some findings"})
            except TypeError:
                 class FunctionCall:
                    def __init__(self, name, args):
                        self.name = name
                        self.args = args
                 fc = FunctionCall(name="report_permissions_matrix", args={"findings": "Some findings"})

            try:
                part = types.Part(function_call=fc)
            except Exception:
                part = types.Part()
                part.function_call = fc

            contents.append(types.Content(role="model", parts=[part]))

            request = LlmRequest(contents=contents, config={})

            # Run generate_content_async
            async def run():
                async for _ in model.generate_content_async(request):
                    pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run())
            finally:
                loop.close()

            # Check messages sent to client
            if mock_client_instance.chat.completions.create.call_args:
                kwargs = mock_client_instance.chat.completions.create.call_args.kwargs
                messages = kwargs.get("messages")

                for msg in messages:
                    if msg["role"] == "assistant":
                        if "tool_calls" in msg:
                            content = msg.get("content")
                            # We expect content to be "" (empty string) not None
                            self.assertIsNotNone(content, "Content should not be None for assistant message with tool calls")
                            self.assertEqual(content, "", "Content should be empty string for assistant message with tool calls")

if __name__ == "__main__":
    unittest.main()
