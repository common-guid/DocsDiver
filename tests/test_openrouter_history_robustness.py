
import asyncio
import os
import unittest
import json
from unittest.mock import MagicMock, AsyncMock
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

class TestOpenRouterHistoryRobustness(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.model = OpenRouterModel(model_name="test-model", api_key="test-key")
        # Mock the OpenAI client
        self.model.client = MagicMock()
        self.model.client.chat.completions.create = AsyncMock()
        
        # Default mock response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Mock response", tool_calls=None))
        ]
        self.model.client.chat.completions.create.return_value = mock_completion

    async def test_string_content_in_history(self):
        """Test that raw strings in history don't cause crashes."""
        request = LlmRequest(
            model="test-model",
            contents=["What is the weather?"]
        )
        
        responses = []
        async for resp in self.model.generate_content_async(request):
            responses.append(resp)
        
        self.assertEqual(len(responses), 1)
        # Verify messages sent to client
        call_args = self.model.client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        self.assertEqual(messages[0], {"role": "user", "content": "What is the weather?"})

    async def test_mixed_content_in_history(self):
        """Test that mixed strings and Content objects work."""
        request = LlmRequest(
            model="test-model",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="I am first")]),
                "I am second (as string)"
            ]
        )
        
        async for _ in self.model.generate_content_async(request): pass
        
        messages = self.model.client.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], {"role": "user", "content": "I am first"})
        self.assertEqual(messages[1], {"role": "user", "content": "I am second (as string)"})

    async def test_system_instruction_handling(self):
        """Test that system instruction is correctly handled whether it is string or object."""
        # Case 1: String system instruction
        config1 = MagicMock()
        config1.system_instruction = "System prompt"
        config1.tools = []
        request1 = LlmRequest(model="m", contents=["hi"], config=config1)
        
        async for _ in self.model.generate_content_async(request1): pass
        messages1 = self.model.client.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(messages1[0], {"role": "system", "content": "System prompt"})

        # Case 2: Content object system instruction
        config2 = MagicMock()
        config2.system_instruction = types.Content(parts=[types.Part.from_text(text="Object system prompt")])
        config2.tools = []
        request2 = LlmRequest(model="m", contents=["hi"], config=config2)
        
        async for _ in self.model.generate_content_async(request2): pass
        messages2 = self.model.client.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(messages2[0], {"role": "system", "content": "Object system prompt"})

    async def test_missing_role_robustness(self):
        """Test that objects missing the role attribute are treated as user."""
        class MockContentNoRole:
            def __init__(self, text):
                self.parts = [types.Part.from_text(text=text)]
        
        request = LlmRequest(
            model="test-model",
            contents=[MockContentNoRole("Mystery role")]
        )
        
        async for _ in self.model.generate_content_async(request): pass
        
        messages = self.model.client.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(messages[0], {"role": "user", "content": "Mystery role"})

if __name__ == "__main__":
    unittest.main()
