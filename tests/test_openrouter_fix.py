
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest
from google.genai import types
import json
from openai import AsyncOpenAI
import os

@pytest.mark.asyncio
async def test_openrouter_history_reconstruction_ids():
    # Setup
    # Create a REAL client but with dummy creds
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")

    # Mock the chat.completions.create method
    # We can't easily swap out the method on the instance if it's frozen or slotted, but let's try.
    # AsyncOpenAI uses normal objects.

    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()

    # We mock the return value just to satisfy the call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Response", tool_calls=None))]
    real_client.chat.completions.create.return_value = mock_response

    # Initialize model with this client
    # We can't pass 'client' to init easily because init creates it.
    # But OpenRouterModel inherits from BaseLlm.
    # If BaseLlm is Pydantic, we might be able to pass 'client' if we override init or patch where it's created.

    # In OpenRouterModel.__init__:
    # client = AsyncOpenAI(...)
    # super().__init__(model=model_name, client=client)

    # So we MUST patch the AsyncOpenAI constructor to return our 'real_client' (which is now modified).

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="test-model", api_key="test-key")

        # Verify our injection worked
        assert model.client == real_client

        # Construct History
        # 1. User: "Use the tool"
        # 2. Model: FunctionCall(name="test_tool") -- NO ID provided
        # 3. Tool: FunctionResponse(name="test_tool", response={...})

        fc = types.FunctionCall(name="test_tool", args={"arg": "val"})
        fr = types.FunctionResponse(name="test_tool", response={"result": "success"})

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text="Use tool")]),
            types.Content(role="model", parts=[types.Part(function_call=fc)]),
            types.Content(role="tool", parts=[types.Part(function_response=fr)])
        ]

        request = LlmRequest(contents=contents, config={})

        # Execute
        async for _ in model.generate_content_async(request):
            pass

        # Verify
        call_args = real_client.chat.completions.create.call_args
        assert call_args is not None

        kwargs = call_args.kwargs
        messages = kwargs["messages"]

        # Check messages structure
        assert messages[0]["role"] == "user"

        # Message 1: Assistant with Tool Call
        assert messages[1]["role"] == "assistant"
        tc = messages[1]["tool_calls"][0]

        # This assertions are expected to FAIL before the fix
        print(f"DEBUG: generated ID: {tc['id']}")

        # We expect it to be deterministic format in the FIX, but for now we expect failure or different format
        assert tc["id"] == "functions.test_tool:0"

        # Message 2: Tool Response
        assert messages[2]["role"] == "tool"
        assert messages[2]["tool_call_id"] == "functions.test_tool:0"
