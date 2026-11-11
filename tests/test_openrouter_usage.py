import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types
from google.adk.models import LlmRequest
from openai.types.chat import ChatCompletion

from sdaa.src.utils.openrouter_model import OpenRouterModel

SLUG = "deepseek/deepseek-v4.1-flash-1017"


def _completion(usage=None, message=None, choices=None):
    if choices is None:
        choices = [{"index": 0, "finish_reason": "stop",
                    "message": message or {"role": "assistant", "content": "hi"}}]
    data = {"id": "gen-1", "object": "chat.completion", "created": 0, "model": SLUG, "choices": choices}
    if usage is not None:
        data["usage"] = usage
    return ChatCompletion.model_validate(data)


USAGE = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
USAGE_COST = {**USAGE, "cost": 0.000016}


async def _run(response, span_setup=None):
    """Run the adapter once with a mocked tracer and client; return (span, tracer, yielded)."""
    with patch("sdaa.src.utils.openrouter_model.trace") as mock_trace:
        tracer = MagicMock()
        mock_trace.get_tracer.return_value = tracer
        span = MagicMock()
        tracer.start_as_current_span.return_value.__enter__.return_value = span
        if span_setup:
            span_setup(span)
        model = OpenRouterModel(model_name=SLUG, api_key="dummy")
        model.client.chat.completions.create = AsyncMock(
            side_effect=response if isinstance(response, Exception) else None,
            return_value=None if isinstance(response, Exception) else response,
        )
        request = LlmRequest(contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])])
        yielded = []
        async for r in model.generate_content_async(request):
            yielded.append(r)
        return span, tracer, yielded


def _attrs(span):
    return {c.args[0]: c.args[1] for c in span.set_attribute.call_args_list}


@pytest.mark.asyncio
async def test_usage_and_cost_recorded():
    span, _, _ = await _run(_completion(usage=USAGE_COST))
    attrs = _attrs(span)
    usage = attrs["langfuse.observation.usage_details"]
    cost = attrs["langfuse.observation.cost_details"]
    assert isinstance(usage, str) and isinstance(cost, str)
    assert json.loads(usage) == {"input": 100, "output": 20, "total": 120}
    assert json.loads(cost) == {"total": 1.6e-05}
    assert not any(k.startswith(("gen_ai.usage", "llm.token_count")) for k in attrs)


@pytest.mark.asyncio
async def test_usage_without_cost():
    span, _, _ = await _run(_completion(usage=USAGE))
    attrs = _attrs(span)
    assert json.loads(attrs["langfuse.observation.usage_details"]) == {"input": 100, "output": 20, "total": 120}
    assert "langfuse.observation.cost_details" not in attrs


@pytest.mark.asyncio
async def test_no_usage():
    span, _, yielded = await _run(_completion(usage=None))
    assert "langfuse.observation.usage_details" not in _attrs(span)
    assert "langfuse.observation.cost_details" not in _attrs(span)
    assert len(yielded) == 1


@pytest.mark.asyncio
async def test_non_numeric_usage_is_ignored():
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "response"
    response.choices[0].message.tool_calls = None
    span, _, yielded = await _run(response)
    attrs = _attrs(span)
    assert "langfuse.observation.usage_details" not in attrs
    assert "langfuse.observation.cost_details" not in attrs
    assert len(yielded) == 1


@pytest.mark.asyncio
async def test_model_name_attribute():
    _, tracer, _ = await _run(_completion(usage=USAGE))
    attributes = tracer.start_as_current_span.call_args.kwargs["attributes"]
    assert attributes["llm.model_name"] == SLUG
    assert "model_name" not in attributes


@pytest.mark.asyncio
async def test_usage_metadata_stays_unset():
    _, _, yielded = await _run(_completion(usage=USAGE_COST))
    assert yielded[0].usage_metadata is None


@pytest.mark.asyncio
async def test_provider_error_still_propagates():
    with pytest.raises(RuntimeError, match="boom"):
        await _run(RuntimeError("boom"))


@pytest.mark.asyncio
async def test_usage_recording_failure_does_not_break_call(caplog):
    def fail_usage_keys(span):
        def set_attribute(key, value):
            if key.startswith("langfuse.observation.usage"):
                raise RuntimeError("span rejected attribute")
        span.set_attribute.side_effect = set_attribute

    with caplog.at_level(logging.WARNING, logger="sdaa.src.utils.openrouter_model"):
        _, _, yielded = await _run(_completion(usage=USAGE_COST), span_setup=fail_usage_keys)
    assert len(yielded) == 1
    assert any("Failed to record OpenRouter usage" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_zero_cost_is_recorded():
    span, _, _ = await _run(_completion(usage={**USAGE, "cost": 0}))
    assert json.loads(_attrs(span)["langfuse.observation.cost_details"]) == {"total": 0}


@pytest.mark.asyncio
async def test_usage_recorded_before_response_parsing_fails():
    bad_tool_call = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "t1", "type": "function", "function": {"name": "f", "arguments": "{not json"}}]}
    spans = []
    with pytest.raises(json.JSONDecodeError):
        await _run(_completion(usage=USAGE_COST, message=bad_tool_call), span_setup=spans.append)
    assert json.loads(_attrs(spans[0])["langfuse.observation.usage_details"])["total"] == 120


@pytest.mark.asyncio
async def test_usage_recorded_when_choices_is_empty():
    with patch("sdaa.src.utils.openrouter_model.trace") as mock_trace:
        tracer = MagicMock()
        mock_trace.get_tracer.return_value = tracer
        span = MagicMock()
        tracer.start_as_current_span.return_value.__enter__.return_value = span
        model = OpenRouterModel(model_name=SLUG, api_key="dummy")
        model.client.chat.completions.create = AsyncMock(
            return_value=_completion(usage=USAGE_COST, choices=[]))
        request = LlmRequest(contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])])
        with pytest.raises(IndexError):
            async for _ in model.generate_content_async(request):
                pass
    assert json.loads(_attrs(span)["langfuse.observation.usage_details"])["total"] == 120
