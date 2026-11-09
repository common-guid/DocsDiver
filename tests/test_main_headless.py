import asyncio
import builtins
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as app
from sdaa.src.core.config_loader import config_loader
from sdaa.src.utils import prompt_manager as prompt_manager_module

# Keyword stubs keyed by Langfuse prompt name. MockModel routes its responses
# on these role phrases, so the stub stands in for the Langfuse-managed
# instructions that are unavailable in CI (see docsdiver_prompt_fallback_defect).
_STUB_PROMPTS = {
    "permissions-agent": "You are the Permissions Analyst. Analyze role based access controls in the documentation.",
    "negative-constraints-agent": "You are the Constraints Analyst. Identify business logic and negative constraints.",
    "security-boundaries-agent": "You are the Boundaries Analyst. Map every security boundary and data flow component.",
    "report-synthesizer": "You are the Principal Security Architect. Synthesize the final report from worker artifacts.",
}


class _StubPrompt:
    def __init__(self, text):
        self._text = text

    def compile(self, **kwargs):
        return self._text


@pytest.fixture(autouse=True)
def _stub_prompts(monkeypatch):
    """Replace Langfuse prompt fetches with keyword-bearing stub instructions."""

    def fake_get_prompt_object(name, label="production", type="text", **kwargs):
        if name in _STUB_PROMPTS:
            return _StubPrompt(_STUB_PROMPTS[name])
        return None

    monkeypatch.setattr(
        prompt_manager_module.prompt_manager,
        "get_prompt_object",
        fake_get_prompt_object,
    )


def _isolate_output_dirs(monkeypatch, tmp_path):
    """Point every config-derived output location at tmp_path."""
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "artifacts").mkdir(exist_ok=True)
    (output_dir / "reports").mkdir(exist_ok=True)

    monkeypatch.setattr(config_loader, "get_output_dir", lambda: str(output_dir))
    monkeypatch.setattr(
        config_loader,
        "get_artifacts_dir",
        lambda: str(output_dir / "artifacts"),
    )
    monkeypatch.setattr(
        config_loader,
        "get_reports_dir",
        lambda: str(output_dir / "reports"),
    )
    return output_dir


def test_headless_mock_audit_writes_all_outputs(monkeypatch, tmp_path):
    """--headless with the mock provider runs the full audit non-interactively.

    MockModel writes the three worker artifacts and the coordinator writes
    Security_Threat_Model.md, so a successful headless run must produce all
    four outputs and never enter the interactive chat loop.
    """
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)
    toc_path = output_dir / config_loader.get("system.toc_filename", "ToC.json")

    async def fake_generate_toc(model=None):
        toc_path.write_text('{"files": []}', encoding="utf-8")

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    chat_entered = {"called": False}

    def _no_chat(*a, **k):  # pragma: no cover - must never run
        chat_entered["called"] = True
        raise AssertionError("Interactive session must not start in headless mode")

    monkeypatch.setattr(builtins, "input", _no_chat)

    monkeypatch.setattr(sys, "argv", ["main.py", "-m", "mock", "--headless", "--no-rich"])

    asyncio.run(app.main())  # SystemExit(1) would propagate; success returns None

    assert not chat_entered["called"]
    assert toc_path.exists()
    artifacts_dir = output_dir / "artifacts"
    reports_dir = output_dir / "reports"
    assert (artifacts_dir / "permissions_agent.md").exists()
    assert (artifacts_dir / "constraints_agent.md").exists()
    assert (artifacts_dir / "boundaries_agent.md").exists()
    assert (reports_dir / "Security_Threat_Model.md").exists()


def test_headless_exits_nonzero_when_outputs_missing(monkeypatch, tmp_path):
    """--headless must exit 1 when the audit leaves outputs missing."""
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)

    async def fake_generate_toc(model=None):
        (output_dir / config_loader.get("system.toc_filename", "ToC.json")).write_text(
            '{"files": []}', encoding="utf-8"
        )

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    # Force the pre-chat audit to fail so outputs stay missing.
    async def broken_prechat(*a, **k):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(app, "build_prechat_audit_agent", broken_prechat)

    monkeypatch.setattr(sys, "argv", ["main.py", "-m", "mock", "--headless", "--no-rich"])

    with pytest.raises(SystemExit) as exc:
        asyncio.run(app.main())
    assert exc.value.code == 1


def test_headless_exits_nonzero_when_prechat_raises_and_outputs_exist(monkeypatch, tmp_path):
    """A raised pre-chat failure must exit 1 even if outputs already exist.

    The missing-output gate already exits 1 when files are absent. This test
    locks the other hole: --coordinator-only runs the audit, the runner
    raises, and stale outputs must not turn that failure into exit 0.
    """
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)
    (output_dir / config_loader.get("system.toc_filename", "ToC.json")).write_text(
        '{"files": []}', encoding="utf-8"
    )
    artifact_text = "existing artifact\n"
    report_text = "existing report\n"
    for name in (
        "permissions_agent.md",
        "constraints_agent.md",
        "boundaries_agent.md",
    ):
        (output_dir / "artifacts" / name).write_text(artifact_text, encoding="utf-8")
    report_path = output_dir / "reports" / "Security_Threat_Model.md"
    report_path.write_text(report_text, encoding="utf-8")

    async def boom(*_a, **_k):
        raise RuntimeError("Error code: 422 - TOKEN_422_SYNTHETIC")

    monkeypatch.setattr(app.RichUI, "stream_response", boom)
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "-m", "mock", "--headless", "--coordinator-only", "--no-rich"],
    )

    with pytest.raises(SystemExit) as exc:
        asyncio.run(app.main())
    assert exc.value.code == 1
    assert report_path.read_text(encoding="utf-8") == report_text
    assert "TOKEN_422_SYNTHETIC" not in report_path.read_text(encoding="utf-8")
    assert "Error calling OpenRouter:" not in report_path.read_text(encoding="utf-8")

