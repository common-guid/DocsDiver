import os
import sys
import builtins
import asyncio

import pytest

# Add the project root to sys.path so 'main' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as app
from sdaa.src.core.config_loader import config_loader
from google.adk.models import BaseLlm


def test_main_generates_toc_when_missing(monkeypatch, tmp_path):
    """When no ToC exists, main should invoke generate_toc and create it.

    This exercises the default behavior with --toc-only so we avoid
    entering the interactive loop.
    """

    def fake_get_output_dir() -> str:
        path = tmp_path / "out_missing"
        os.makedirs(path, exist_ok=True)
        return str(path)

    monkeypatch.setattr(config_loader, "get_output_dir", fake_get_output_dir)

    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = tmp_path / "out_missing"
    toc_path = output_dir / toc_filename

    if toc_path.exists():
        toc_path.unlink()

    calls = {"count": 0}

    async def fake_generate_toc(model=None):  # pragma: no cover - behavior validated via side effects
        calls["count"] += 1
        output_dir.mkdir(parents=True, exist_ok=True)
        toc_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    # Use --toc-only to exit before interactive session
    # We also use --no-rich to avoid terminal escape codes in test output
    monkeypatch.setattr(sys, "argv", ["main.py", "--toc-only", "--no-rich"])

    asyncio.run(app.main())

    assert calls["count"] == 1
    assert toc_path.exists()


def test_main_skips_toc_generation_when_file_exists(monkeypatch, tmp_path):
    """If a ToC already exists at the resolved path, main should skip Map Maker."""

    def fake_get_output_dir() -> str:
        path = tmp_path / "out_existing"
        os.makedirs(path, exist_ok=True)
        return str(path)

    monkeypatch.setattr(config_loader, "get_output_dir", fake_get_output_dir)

    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = tmp_path / "out_existing"
    toc_path = output_dir / toc_filename

    output_dir.mkdir(parents=True, exist_ok=True)
    toc_path.write_text("{}", encoding="utf-8")
    artifacts_dir = output_dir / config_loader.get("system.artifacts_dir", "artifacts")
    reports_dir = output_dir / config_loader.get("system.reports_dir", "reports")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    (artifacts_dir / "permissions_agent.md").write_text("perm", encoding="utf-8")
    (artifacts_dir / "constraints_agent.md").write_text("constraints", encoding="utf-8")
    (artifacts_dir / "boundaries_agent.md").write_text("boundaries", encoding="utf-8")
    (reports_dir / "Security_Threat_Model.md").write_text("report", encoding="utf-8")

    calls = {"count": 0}

    async def fake_generate_toc(model=None):  # pragma: no cover - we assert this is never called
        calls["count"] += 1

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    monkeypatch.setattr(sys, "argv", ["main.py", "--toc-only", "--no-rich"])

    asyncio.run(app.main())

    assert calls["count"] == 0
    # Existing ToC is preserved
    assert toc_path.exists()


def test_main_honors_skip_flag_even_without_toc(monkeypatch, tmp_path):
    """With --skip-map-maker, main should not call generate_toc even if ToC is missing."""

    def fake_get_output_dir() -> str:
        path = tmp_path / "out_skip_flag"
        os.makedirs(path, exist_ok=True)
        return str(path)

    monkeypatch.setattr(config_loader, "get_output_dir", fake_get_output_dir)

    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = tmp_path / "out_skip_flag"
    toc_path = output_dir / toc_filename

    if toc_path.exists():
        toc_path.unlink()

    calls = {"count": 0}

    async def fake_generate_toc(model=None):  # pragma: no cover - we assert no calls
        calls["count"] += 1

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    monkeypatch.setattr(sys, "argv", ["main.py", "--skip-map-maker", "--toc-only", "--no-rich"])

    asyncio.run(app.main())

    assert calls["count"] == 0
    # ToC should still be absent unless created out-of-band by the user
    assert not toc_path.exists()


class _DummyModel(BaseLlm):
    """Minimal stand-in for Gemini/OpenRouter/MockModel in CLI tests."""
    model: str = "dummy-model"

    def __init__(self, model=None, model_name=None, base_url=None, **kwargs):  # pragma: no cover - trivial init
        # Preserve a model identifier so downstream code can inspect it if needed
        super().__init__(model=model or model_name or "dummy-model", **kwargs)

    async def generate_content_async(self, request, stream=False):  # pragma: no cover - not exercised in these tests
        if False:
            yield None



def test_skip_map_maker_with_existing_toc_still_initializes_agents(monkeypatch, tmp_path):
    """Ensure that skipping Map Maker with an existing ToC still starts the coordinator.

    This simulates the common workflow where a user precomputes ToC.json, then
    runs SDAA with --skip-map-maker so agents can immediately consume the
    existing map.
    """

    def fake_get_output_dir() -> str:
        path = tmp_path / "out_agents"
        os.makedirs(path, exist_ok=True)
        return str(path)

    monkeypatch.setattr(config_loader, "get_output_dir", fake_get_output_dir)

    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = tmp_path / "out_agents"
    toc_path = output_dir / toc_filename

    output_dir.mkdir(parents=True, exist_ok=True)
    toc_path.write_text("{}", encoding="utf-8")

    async def fake_generate_toc(model=None):  # pragma: no cover - must not be called
        raise AssertionError("generate_toc should not be called when --skip-map-maker is set")

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    # Stub models and runner to avoid external dependencies
    monkeypatch.setattr(app, "OpenRouterModel", _DummyModel)
    monkeypatch.setattr(app, "Gemini", _DummyModel)
    monkeypatch.setattr(app, "MockModel", _DummyModel)

    # Capture that the coordinator is created successfully
    created = {"agent": None}
    real_create = app.create_coordinator_agent

    def fake_create_coordinator_agent(provider=None, model=None):  # pragma: no cover - minimal wrapper
        created["agent"] = real_create(provider=provider, model=model)
        return created["agent"]

    monkeypatch.setattr(app, "create_coordinator_agent", fake_create_coordinator_agent)

    # Exit the interactive loop immediately
    monkeypatch.setattr(builtins, "input", lambda prompt="": "exit")

    monkeypatch.setattr(sys, "argv", ["main.py", "--skip-map-maker", "--no-rich"])

    asyncio.run(app.main())

    assert created["agent"] is not None
    assert toc_path.exists()
