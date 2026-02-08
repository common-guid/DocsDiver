import pytest
import os
import shutil
import asyncio
from unittest.mock import MagicMock
from sdaa.src.tools.context_ops import context_manager, reset_context, append_to_notebook, read_notebook
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils.shared_session_service import SharedMemorySessionService
try:
    from google.adk.sessions import InMemorySessionService
except ImportError:
    InMemorySessionService = None

# Setup test output dir
TEST_OUTPUT_DIR = "tests/test_output_context"

@pytest.fixture
def setup_env():
    # Patch config_loader to point to test dir
    original_get_output_dir = config_loader.get_output_dir
    original_get_artifacts_dir = config_loader.get_artifacts_dir

    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    artifacts_dir = os.path.join(TEST_OUTPUT_DIR, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    config_loader.get_output_dir = MagicMock(return_value=TEST_OUTPUT_DIR)
    config_loader.get_artifacts_dir = MagicMock(return_value=artifacts_dir)

    yield

    # Cleanup
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)
    config_loader.get_output_dir = original_get_output_dir
    config_loader.get_artifacts_dir = original_get_artifacts_dir

def test_reset_context_keeps_last_event(setup_env):
    if not InMemorySessionService:
        pytest.skip("google-adk not installed")

    async def run_async_test():
        service = SharedMemorySessionService()
        app = "test_app"
        user = "test_user"
        sess_id = "test_sess"

        session = await service.create_session(app_name=app, user_id=user, session_id=sess_id)

        # Register
        context_manager.register_session(service, app, user, sess_id)

        # Add dummy events
        # We need to simulate the structure. InMemorySessionService stores whatever we put in events list.
        session.events.append("Event 1 (User)")
        session.events.append("Event 2 (Model)")
        session.events.append("Event 3 (User)")
        session.events.append("Event 4 (Model - Tool Call)")

        assert len(session.events) == 4

        # Call reset
        msg = reset_context(summary="Processed 2 files.")

        assert "Context reset successfully" in msg
        assert "Processed 2 files" in msg

        # Verify events
        # Should only have the last event
        assert len(session.events) == 1
        assert session.events[0] == "Event 4 (Model - Tool Call)"

    asyncio.run(run_async_test())

def test_notebook_operations(setup_env):
    agent_name = "test_agent"
    content = "Found issue in auth.md"

    # Append
    res = append_to_notebook(agent_name, content)
    assert "Content appended" in res

    # Verify file exists
    artifacts_dir = config_loader.get_artifacts_dir()
    notebook_path = os.path.join(artifacts_dir, "notebooks", f"{agent_name}.md")
    assert os.path.exists(notebook_path)

    # Read back
    read_content = read_notebook(agent_name)
    assert content in read_content

    # Append more
    append_to_notebook(agent_name, "Another finding")
    read_content_2 = read_notebook(agent_name)
    assert content in read_content_2
    assert "Another finding" in read_content_2
