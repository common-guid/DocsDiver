import pytest
import os
import sys
import json
import asyncio
from google.genai import types

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as app
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.mock_model import MockModel
from sdaa.src.core.map_maker import generate_toc
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
import sdaa.src.tools.file_ops as file_ops_module

@pytest.mark.asyncio
async def test_artifact_generation_flow(monkeypatch, tmp_path):
    # 1. Setup paths
    output_dir = tmp_path / "output"
    os.makedirs(output_dir, exist_ok=True)

    reports_dir = output_dir / "reports"
    artifacts_dir = output_dir / "artifacts"

    # 2. Mock ConfigLoader
    # ConfigLoader is a singleton, so we patch get_output_dir on the class or instance.
    monkeypatch.setattr(config_loader, "get_output_dir", lambda: str(output_dir))

    # 3. Mock file_ops to avoid reading real FS
    def fake_list_files(path: str = ".") -> str:
        return "docs/auth.md\ndocs/billing.md\ndocs/api.md"

    def fake_read_file(filepath: str) -> str:
        return f"# Content for {filepath}"

    # Patching where the tools are defined/imported
    # Since modules often do "from x import y", we must patch y in the module that uses it.

    import sdaa.src.core.map_maker as map_maker_module
    monkeypatch.setattr(map_maker_module, "list_files", fake_list_files)
    monkeypatch.setattr(map_maker_module, "read_file", fake_read_file)

    import sdaa.src.agents.workers as workers_module
    monkeypatch.setattr(workers_module, "list_files", fake_list_files)
    monkeypatch.setattr(workers_module, "read_file", fake_read_file)

    import sdaa.src.agents.coordinator as coordinator_module
    monkeypatch.setattr(coordinator_module, "read_file", fake_read_file)

    # 4. Run Map Maker
    model = MockModel(model="mock-model")
    await generate_toc(model=model)

    toc_path = output_dir / "ToC.json"
    assert toc_path.exists()

    with open(toc_path, "r") as f:
        toc_data = json.load(f)
        assert "files" in toc_data
        assert len(toc_data["files"]) == 3

    # 5. Run Pre-chat Audit
    # We use build_prechat_audit_agent from main.py
    agent = app.build_prechat_audit_agent(provider="mock")

    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    runner = Runner(
        agent=agent,
        app_name="sdaa_test",
        session_service=session_service,
        memory_service=memory_service
    )

    user_id = "test_user"
    session_id = "test_session"
    # Ensure session exists
    await session_service.create_session(app_name="sdaa_test", user_id=user_id, session_id=session_id)

    # Run the agent
    print("Starting runner...")
    response_stream = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(parts=[types.Part.from_text(text="Audit the application")])
    )

    # Consume the stream
    async for response in response_stream:
        # We could inspect response here if needed
        pass
    print("Runner finished.")

    # 6. Verify Artifacts
    print(f"Checking artifacts in {artifacts_dir}")
    assert (artifacts_dir / "permissions_agent.md").exists(), "permissions_agent.md not found"
    assert (artifacts_dir / "constraints_agent.md").exists(), "constraints_agent.md not found"
    assert (artifacts_dir / "boundaries_agent.md").exists(), "boundaries_agent.md not found"
    assert (reports_dir / "Security_Threat_Model.md").exists(), "Security_Threat_Model.md not found"

    # Verify content
    with open(reports_dir / "Security_Threat_Model.md", "r") as f:
        content = f.read()
        assert "Master Audit Report" in content

    with open(artifacts_dir / "permissions_agent.md", "r") as f:
        content = f.read()
        assert "RBAC Analysis" in content

    with open(artifacts_dir / "boundaries_agent.md", "r") as f:
        content = f.read()
        assert "Boundaries Analysis" in content
