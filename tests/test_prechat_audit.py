import os
import sys

# Add the project root to sys.path so 'main' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as app
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.mock_model import MockModel


def test_audit_output_problems_tracks_the_four_outputs(monkeypatch, tmp_path):
    def fake_get_output_dir() -> str:
        path = tmp_path / "out_prechat"
        os.makedirs(path, exist_ok=True)
        return str(path)

    monkeypatch.setattr(config_loader, "get_output_dir", fake_get_output_dir)

    assert len(app.audit_output_problems()) == 4

    artifacts_dir = config_loader.get_artifacts_dir()
    reports_dir = config_loader.get_reports_dir()

    with open(os.path.join(artifacts_dir, "permissions_agent.md"), "w", encoding="utf-8") as f:
        f.write("perm")
    with open(os.path.join(artifacts_dir, "constraints_agent.md"), "w", encoding="utf-8") as f:
        f.write("constraints")
    with open(os.path.join(artifacts_dir, "boundaries_agent.md"), "w", encoding="utf-8") as f:
        f.write("boundaries")
    with open(os.path.join(reports_dir, "Security_Threat_Model.md"), "w", encoding="utf-8") as f:
        f.write("report")

    assert app.audit_output_problems() == []


def test_build_prechat_audit_agent_order():
    agent = app.build_prechat_audit_agent(MockModel(model="mock-model"))
    names = [sub_agent.name for sub_agent in agent.sub_agents]
    assert names == [
        "permissions_agent",
        "constraints_agent",
        "boundaries_agent",
        "coordinator_psa",
    ]


def test_failed_artifact_write_propagates_through_adk_runner(monkeypatch, tmp_path):
    """Pins ADK behavior: an exception raised by a reporting tool escapes Runner.run_async.

    If a future ADK swallowed tool errors, a failed write would look like success.
    """
    import asyncio

    import pytest
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from sdaa.src.tools.reporting import report_permissions_matrix
    from sdaa.src.utils.artifact_loader_model import ArtifactLoaderModel

    monkeypatch.setattr(config_loader, "get_artifacts_dir", lambda: str(tmp_path / "missing" / "dir"))
    agent = LlmAgent(
        name="permissions_agent",
        model=ArtifactLoaderModel(
            content="# findings", tool_name="report_permissions_matrix", tool_arg_name="findings"
        ),
        tools=[report_permissions_matrix],
    )

    async def run():
        svc = InMemorySessionService()
        runner = Runner(agent=agent, app_name="t", session_service=svc)
        await svc.create_session(app_name="t", user_id="u", session_id="s")
        msg = types.Content(role="user", parts=[types.Part.from_text(text="go")])
        async for _ in runner.run_async(user_id="u", session_id="s", new_message=msg):
            pass

    with pytest.raises(OSError):
        asyncio.run(run())


# --- Synthesis reads artifact bodies from disk (Tactical 3, D5) ---
import asyncio

import pytest

from sdaa.src.utils import prompt_manager as prompt_manager_module

_ROLE_TEXT = {
    "permissions-agent": "You are the Permissions Analyst. Analyze role based access controls.",
    "negative-constraints-agent": "You are the Constraints Analyst. Identify business logic and negative constraints.",
    "security-boundaries-agent": "You are the Boundaries Analyst. Map every security boundary and data flow component.",
    "report-synthesizer": "You are the Principal Security Architect. Synthesize the final report.",
}


@pytest.fixture
def synth_kwargs(monkeypatch):
    """Stub Langfuse prompts; record the kwargs the synthesizer prompt is compiled with."""
    recorded = {}

    class _Prompt:
        def __init__(self, name):
            self.name = name

        def compile(self, **kwargs):
            if self.name == "report-synthesizer":
                recorded.update(kwargs)
            return _ROLE_TEXT[self.name]

    monkeypatch.setattr(
        prompt_manager_module.prompt_manager,
        "get_prompt_object",
        lambda name, label="production", type="text", **kw: _Prompt(name) if name in _ROLE_TEXT else None,
    )
    return recorded


def _run_prechat():
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    async def run():
        svc = InMemorySessionService()
        runner = Runner(agent=app.build_prechat_audit_agent("mock"), app_name="t", session_service=svc)
        await svc.create_session(app_name="t", user_id="u", session_id="s")
        msg = types.Content(role="user", parts=[types.Part.from_text(text="Audit")])
        async for _ in runner.run_async(user_id="u", session_id="s", new_message=msg):
            pass

    asyncio.run(run())


def test_synthesis_receives_replayed_artifact_bodies(synth_kwargs):
    artifacts = config_loader.get_artifacts_dir()
    tokens = {"permissions": "TOKEN_PERM_ab12", "constraints": "TOKEN_CONS_cd34", "boundaries": "TOKEN_BOUND_ef56"}
    for name, token in tokens.items():
        with open(os.path.join(artifacts, f"{name}_agent.md"), "w", encoding="utf-8") as f:
            f.write(f"# findings\n{token}\n")

    _run_prechat()

    assert tokens["permissions"] in synth_kwargs["permissions_report"]
    assert tokens["constraints"] in synth_kwargs["constraints_report"]
    assert tokens["boundaries"] in synth_kwargs["boundaries_report"]
    for v in synth_kwargs.values():
        assert "Artifact loaded" not in v


def test_synthesis_receives_findings_on_fresh_mock_run(synth_kwargs):
    _run_prechat()
    assert "# RBAC Analysis" in synth_kwargs["permissions_report"]
    for v in synth_kwargs.values():
        assert "recorded and saved" not in v and "MISSING" not in v


def test_synthesis_sanitizes_braces_in_artifact_bodies(synth_kwargs):
    artifacts = config_loader.get_artifacts_dir()
    for name in ("permissions", "constraints", "boundaries"):
        with open(os.path.join(artifacts, f"{name}_agent.md"), "w", encoding="utf-8") as f:
            f.write("user {user_id} and {{literal}}")
    _run_prechat()
    assert "(user_id)" in synth_kwargs["permissions_report"]
    assert "{user_id}" not in synth_kwargs["permissions_report"]
