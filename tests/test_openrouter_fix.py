
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


def _completion_with(message):
    response = MagicMock()
    response.choices = [MagicMock(message=message)]
    return response


def _tool_call(tc_id, name, arguments):
    tool_call = MagicMock()
    tool_call.id = tc_id
    tool_call.function.name = name
    tool_call.function.arguments = arguments
    return tool_call


@pytest.mark.asyncio
async def test_response_preserves_provider_tool_call_ids():
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")
    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()

    first = MagicMock()
    first.content = None
    first.reasoning_details = None
    first.tool_calls = [
        _tool_call("call_prov_a", "audit_tool", '{"n": 1}'),
        _tool_call("call_prov_b", "audit_tool", '{"n": 2}'),
    ]
    second = MagicMock()
    second.content = "done"
    second.tool_calls = None
    second.reasoning_details = None
    real_client.chat.completions.create.side_effect = [
        _completion_with(first),
        _completion_with(second),
    ]

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="x-ai/grok-4.1-fast", api_key="test-key")
        first_request = LlmRequest(
            contents=[types.Content(role="user", parts=[types.Part.from_text(text="Audit")])],
            config={},
        )
        responses = []
        async for resp in model.generate_content_async(first_request):
            responses.append(resp)

        calls = [p.function_call for p in responses[0].content.parts if p.function_call]
        assert [c.id for c in calls] == ["call_prov_a", "call_prov_b"]
        assert [c.name for c in calls] == ["audit_tool", "audit_tool"]

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text="Audit")]),
            types.Content(role="model", parts=[types.Part(function_call=c) for c in calls]),
            types.Content(role="user", parts=[
                types.Part(function_response=types.FunctionResponse(
                    name="audit_tool", response={"ok": True}, id="call_prov_a"
                )),
                types.Part(function_response=types.FunctionResponse(
                    name="audit_tool", response={"ok": True}, id="call_prov_b"
                )),
            ]),
        ]
        async for _ in model.generate_content_async(LlmRequest(contents=contents, config={})):
            pass

    second_kwargs = real_client.chat.completions.create.call_args_list[1].kwargs
    assert second_kwargs["model"] == "x-ai/grok-4.1-fast"
    assert second_kwargs["extra_body"] == {"reasoning": {"enabled": True}}
    messages = second_kwargs["messages"]
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert [tc["id"] for tc in assistant["tool_calls"]] == ["call_prov_a", "call_prov_b"]
    assert [m["tool_call_id"] for m in messages if m["role"] == "tool"] == [
        "call_prov_a",
        "call_prov_b",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_id", [None, ""])
async def test_response_missing_or_empty_provider_id_uses_fallback(provider_id):
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")
    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()

    message = MagicMock()
    message.content = None
    message.reasoning_details = None
    message.tool_calls = [_tool_call(provider_id, "audit_tool", "{}")]
    real_client.chat.completions.create.return_value = _completion_with(message)

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="test-model", api_key="test-key")
        request = LlmRequest(
            contents=[types.Content(role="user", parts=[types.Part.from_text(text="Audit")])],
            config={},
        )
        responses = []
        async for resp in model.generate_content_async(request):
            responses.append(resp)

    calls = [p.function_call for p in responses[0].content.parts if p.function_call]
    assert [c.id for c in calls] == ["functions.audit_tool:0"]


@pytest.mark.asyncio
async def test_tool_schema_preserves_array_items():
    real_client = AsyncOpenAI(api_key="dummy", base_url="http://dummy")
    real_client.chat = MagicMock()
    real_client.chat.completions = MagicMock()
    real_client.chat.completions.create = AsyncMock()
    message = MagicMock()
    message.content = "ok"
    message.tool_calls = None
    message.reasoning_details = None
    real_client.chat.completions.create.return_value = _completion_with(message)

    tool = types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="audit_tool",
            description="Record an audit finding.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "finding": types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "severity": types.Schema(type=types.Type.STRING, description="sev"),
                        },
                        required=["severity"],
                    ),
                    "tags": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING, description="tag"),
                    ),
                    "evidence": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "quotes": types.Schema(
                                    type=types.Type.ARRAY,
                                    items=types.Schema(type=types.Type.STRING),
                                ),
                            },
                            required=["quotes"],
                        ),
                    ),
                    "notes": types.Schema(type=types.Type.ARRAY),
                },
                required=["finding", "tags", "evidence"],
            ),
        )
    ])
    request = LlmRequest(
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="Audit")])],
        config=types.GenerateContentConfig(tools=[tool]),
    )

    with patch("sdaa.src.utils.openrouter_model.AsyncOpenAI", return_value=real_client):
        model = OpenRouterModel(model_name="test-model", api_key="test-key")
        async for _ in model.generate_content_async(request):
            pass

    params = real_client.chat.completions.create.call_args.kwargs["tools"][0]["function"]["parameters"]
    assert params["required"] == ["finding", "tags", "evidence"]
    assert params["properties"]["finding"]["properties"]["severity"]["type"] == "string"
    assert params["properties"]["finding"]["required"] == ["severity"]
    assert params["properties"]["tags"]["type"] == "array"
    assert params["properties"]["tags"]["items"]["type"] == "string"
    quotes = params["properties"]["evidence"]["items"]["properties"]["quotes"]
    assert quotes["type"] == "array"
    assert quotes["items"]["type"] == "string"
    assert params["properties"]["evidence"]["items"]["required"] == ["quotes"]
    assert "items" not in params["properties"]["notes"]
