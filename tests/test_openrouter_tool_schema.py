"""Regression: OpenRouter tool conversion with declarations built by ADK itself.

google-adk 2.14 emits FunctionDeclaration(parameters=None, parameters_json_schema={...}).
The older tests hand-build parameters=types.Schema, which ADK no longer produces.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from google.adk.models import BaseLlm, LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent
from google.genai import types

from sdaa.src.agents.coordinator import create_coordinator_agent, create_coordinator_synthesizer
from sdaa.src.agents.workers import create_permissions_agent
from sdaa.src.utils.openrouter_model import OpenRouterModel


class _Recorder(BaseLlm):
    """Model that records the LlmRequest ADK builds, then ends the turn."""
    model: str = "recorder"
    requests: list = []

    async def generate_content_async(self, llm_request, stream=False):
        self.requests.append(llm_request)
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part.from_text(text="done")]))


def _capture(agent_factory):
    """Run a real ADK agent once and return the LlmRequests it sent to the model."""
    rec = _Recorder()
    rec.requests = []

    async def go():
        agent = agent_factory(rec)
        svc = InMemorySessionService()
        runner = Runner(agent=agent, app_name="t", session_service=svc)
        await svc.create_session(app_name="t", user_id="u", session_id="s")
        msg = types.Content(role="user", parts=[types.Part.from_text(text="hi")])
        async for _ in runner.run_async(user_id="u", session_id="s", new_message=msg):
            pass

    asyncio.run(go())
    return rec.requests


def _payload_tools(llm_request):
    """Send an ADK-built LlmRequest through OpenRouterModel; return the `tools` sent to the client."""
    model = OpenRouterModel(model_name="test/model", api_key="dummy")
    msg = MagicMock(content="ok", tool_calls=None, reasoning_details=None)
    create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=msg)], usage=None))
    model.client = MagicMock()
    model.client.chat.completions.create = create

    async def go():
        async for _ in model.generate_content_async(llm_request):
            pass

    asyncio.run(go())
    return {t["function"]["name"]: t for t in create.call_args.kwargs["tools"]}


def _declared_as_adk_2_14(llm_request):
    for tool in llm_request.config.tools:
        for fd in tool.function_declarations:
            assert fd.parameters is None and fd.parameters_json_schema, (
                "ADK no longer emits this shape; update the test"
            )


def test_worker_tools_convert_from_adk_json_schema():
    req = _capture(lambda m: create_permissions_agent(model=m))[0]
    _declared_as_adk_2_14(req)
    tools = _payload_tools(req)

    assert set(tools) == {"read_file", "list_files", "report_permissions_matrix"}
    for t in tools.values():
        assert t["type"] == "function"
        assert t["function"]["parameters"]["type"] == "object"

    read = tools["read_file"]["function"]["parameters"]
    assert read["properties"]["file_path"]["type"] == "string"
    assert read["required"] == ["file_path"]

    listing = tools["list_files"]["function"]["parameters"]
    assert "directory_path" in listing["properties"]
    assert not listing.get("required")  # optional: has a default

    report = tools["report_permissions_matrix"]["function"]["parameters"]
    assert report["required"] == ["findings"]


def test_synthesizer_generate_final_report_converts():
    req = _capture(lambda m: create_coordinator_synthesizer(model=m))[0]
    _declared_as_adk_2_14(req)
    params = _payload_tools(req)["generate_final_report"]["function"]["parameters"]
    assert params["properties"]["report_content"]["type"] == "string"
    assert params["required"] == ["report_content"]


def test_coordinator_transfer_to_agent_converts():
    req = _capture(lambda m: create_coordinator_agent(model=m))[0]
    _declared_as_adk_2_14(req)
    tools = _payload_tools(req)
    assert {"transfer_to_agent", "read_file", "generate_final_report"} <= set(tools)
    params = tools["transfer_to_agent"]["function"]["parameters"]
    assert params["required"] == ["agent_name"]
    assert set(params["properties"]["agent_name"]["enum"]) == {
        "permissions_agent", "constraints_agent", "boundaries_agent",
    }


def test_array_items_survive_json_schema_path_including_nested():
    def record(tags: list[str], matrix: list[list[int]], note: str = "") -> str:
        """Record things."""
        return "ok"

    req = _capture(lambda m: LlmAgent(name="a", model=m, tools=[record]))[0]
    _declared_as_adk_2_14(req)
    props = _payload_tools(req)["record"]["function"]["parameters"]["properties"]
    assert props["tags"]["type"] == "array" and props["tags"]["items"]["type"] == "string"
    assert props["matrix"]["items"]["type"] == "array"
    assert props["matrix"]["items"]["items"]["type"] == "integer"


def test_zero_argument_tool_gets_empty_object_schema():
    def ping() -> str:
        """Ping."""
        return "pong"

    req = _capture(lambda m: LlmAgent(name="a", model=m, tools=[ping]))[0]
    params = _payload_tools(req)["ping"]["function"]["parameters"]
    assert params["type"] == "object"
    assert not params.get("properties")


def test_declaration_with_no_schema_falls_back_to_empty_object():
    model = OpenRouterModel(model_name="test/model", api_key="dummy")
    tool = types.Tool(function_declarations=[types.FunctionDeclaration(name="bare", description="d")])
    out = model._convert_tools([tool])
    assert out[0]["function"]["parameters"] == {"type": "object", "properties": {}}
