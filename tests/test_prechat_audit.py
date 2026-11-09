import os
import sys

# Add the project root to sys.path so 'main' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as app
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.mock_model import MockModel


def test_get_missing_prechat_outputs(monkeypatch, tmp_path):
    def fake_get_output_dir() -> str:
        path = tmp_path / "out_prechat"
        os.makedirs(path, exist_ok=True)
        return str(path)

    monkeypatch.setattr(config_loader, "get_output_dir", fake_get_output_dir)

    missing = app.get_missing_prechat_outputs()
    assert len(missing) == 4

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

    missing = app.get_missing_prechat_outputs()
    assert missing == []


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
