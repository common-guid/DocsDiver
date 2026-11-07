"""Shared test fixtures.

Makes the test suite hermetic: OpenRouterModel() requires an API key at
construction time (falls back to OPENROUTER_API_KEY, then OPENAI_API_KEY, then
raises). On dev machines a real .env provided this; CI must not need one.
"""
import os

import pytest


@pytest.fixture(autouse=True)
def _dummy_llm_env(monkeypatch):
    """Provide dummy LLM credentials so model construction never touches secrets."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    # Keep observability off in tests: no external endpoints, no trace export.
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:1")
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
