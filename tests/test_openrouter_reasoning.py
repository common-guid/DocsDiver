import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
import json
from openai.types.chat import ChatCompletionMessage
from openai import AsyncOpenAI

REASONING_MIME_TYPE = "application/x-reasoning-details"

@pytest.mark.asyncio
async def test_grok_reasoning_parameter():
    # Setup
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")
    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=ChatCompletionMessage(role="assistant", content="Response"))]
    real_client.chat.completions.create.return_value = mock_response

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="x-ai/grok-4.1-fast", api_key="test-key")

        request = LlmRequest(contents=[types.Content(role="user", parts=[types.Part.from_text(text="Hi")])], config={})

        async for _ in model.generate_content_async(request):
            pass

        # Verify extra_body={"reasoning": {"enabled": True}} was passed
        call_args = real_client.chat.completions.create.call_args
        assert call_args is not None
        kwargs = call_args.kwargs

        assert "extra_body" in kwargs
        assert kwargs["extra_body"] == {"reasoning": {"enabled": True}}

@pytest.mark.asyncio
async def test_reasoning_persistence_request():
    # Verify that if we have a part with reasoning inline_data, it gets into the message
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")
    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=ChatCompletionMessage(role="assistant", content="Response"))]
    real_client.chat.completions.create.return_value = mock_response

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="x-ai/grok-4.1-fast", api_key="test-key")

        # Construct history with a reasoning part
        reasoning_data = {"steps": ["step1", "step2"]}
        blob = types.Blob(mime_type=REASONING_MIME_TYPE, data=json.dumps(reasoning_data).encode("utf-8"))

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text="Hi")]),
            types.Content(role="model", parts=[
                types.Part.from_text(text="Thinking..."),
                types.Part(inline_data=blob)
            ])
        ]

        request = LlmRequest(contents=contents, config={})

        async for _ in model.generate_content_async(request):
            pass

        call_args = real_client.chat.completions.create.call_args
        kwargs = call_args.kwargs
        messages = kwargs["messages"]

        # Check second message (assistant)
        assistant_msg = messages[1]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == "Thinking..."
        # We explicitly DO NOT want reasoning_details to be sent back to the model as input
        # to avoid "untagged enum ModelInput" errors from strict providers like xAI.
        assert "reasoning_details" not in assistant_msg

@pytest.mark.asyncio
async def test_reasoning_persistence_response():
    # Verify that if API returns reasoning_details, we capture it in LlmResponse
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")
    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()

    reasoning_payload = {"trace_id": "123", "tokens": 50}

    # Construct a message with extra field. ChatCompletionMessage supports this.
    msg = ChatCompletionMessage(role="assistant", content="Answer", reasoning_details=reasoning_payload)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=msg)]
    real_client.chat.completions.create.return_value = mock_response

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="x-ai/grok-4.1-fast", api_key="test-key")
        request = LlmRequest(contents=[types.Content(role="user", parts=[types.Part.from_text(text="Hi")])], config={})

        responses = []
        async for resp in model.generate_content_async(request):
            responses.append(resp)

        assert len(responses) == 1
        content = responses[0].content

        # Should have text part and inline_data part
        assert len(content.parts) == 2

        # Find the inline_data part
        reasoning_part = next((p for p in content.parts if p.inline_data and p.inline_data.mime_type == REASONING_MIME_TYPE), None)
        assert reasoning_part is not None

        data = json.loads(reasoning_part.inline_data.data.decode("utf-8"))
        assert data == reasoning_payload
