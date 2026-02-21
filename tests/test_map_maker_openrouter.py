import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from sdaa.src.utils.openrouter_model import OpenRouterModel
from google.adk.models import LlmRequest
from google.genai import types

@pytest.mark.asyncio
async def test_openrouter_model_history_handling():
    # Mock AsyncOpenAI client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = '{"summary": "Test", "tags": ["a", "b", "c"]}'
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    mock_client.chat.completions.create.return_value = mock_response
    
    model = OpenRouterModel(model_name="test-model", api_key="test-key")
    model.client = mock_client
    
    # Test case 1: Contents as a list (standard)
    prompt = "Test prompt"
    request = LlmRequest(
        model="test-model",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    )
    
    async for response in model.generate_content_async(request):
        assert response.content.parts[0].text == mock_message.content
        
    # Check if messages were correctly passed to OpenAI
    args, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs.get('messages')
    assert len(messages) == 1
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == prompt

@pytest.mark.asyncio
async def test_openrouter_model_empty_contents():
    # Mock AsyncOpenAI client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Response"
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    
    model = OpenRouterModel(model_name="test-model", api_key="test-key")
    model.client = mock_client
    
    # Test case: Contents as None
    request = LlmRequest(model="test-model", contents=None)
    
    # Should not crash, but messages will be empty (and logger will warn)
    async for response in model.generate_content_async(request):
        pass
    
    args, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs.get('messages')
    assert messages == []

@pytest.mark.asyncio
async def test_openrouter_model_tuple_contents():
    # Mock AsyncOpenAI client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Response"
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    
    model = OpenRouterModel(model_name="test-model", api_key="test-key")
    model.client = mock_client
    
    # Test case: Contents as a tuple (which was failing before)
    prompt = "Tuple prompt"
    request = LlmRequest(
        model="test-model",
        contents=(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),)
    )
    
    async for response in model.generate_content_async(request):
        pass
        
    args, kwargs = mock_client.chat.completions.create.call_args
    messages = kwargs.get('messages')
    assert len(messages) == 1
    assert messages[0]['content'] == prompt
