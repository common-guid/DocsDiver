"""Shared test fixtures.

Makes the test suite hermetic: OpenRouterModel() requires an API key at
construction time (falls back to OPENROUTER_API_KEY, then OPENAI_API_KEY, then
raises). On dev machines a real .env provided this; CI must not need one.
"""
import json
import os

import pytest

from sdaa.src.core.config_loader import config_loader


@pytest.fixture(autouse=True)
def _dummy_llm_env(monkeypatch):
    """Provide dummy LLM credentials so model construction never touches secrets."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    # Keep observability off in tests: no external endpoints, no trace export.
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:1")
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)


@pytest.fixture(autouse=True)
def _isolated_output_dir(monkeypatch, tmp_path):
    """Send every test's outputs (ToC, artifacts, reports) to a per-test tmp dir.

    get_reports_dir/get_artifacts_dir derive from get_output_dir, so this one patch
    keeps the user's real ./output untouched. Tests that patch it again still win.
    """
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(config_loader, "get_output_dir", lambda: str(out))


@pytest.fixture
def write_valid_toc():
    """Return a function that writes a ToC valid against docs-for-testing/."""

    def _write(path):
        entries = [
            {"path": name, "summary": f"Summary of {name}.", "tags": ["alpha", "beta", "gamma"]}
            for name in ("auth.md", "billing.md")
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"files": entries}, f)

    return _write
