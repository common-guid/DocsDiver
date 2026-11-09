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


def test_headless_mock_audit_writes_all_outputs(monkeypatch, tmp_path, write_valid_toc):
    """--headless with the mock provider runs the full audit non-interactively.

    MockModel writes the three worker artifacts and the coordinator writes
    Security_Threat_Model.md, so a successful headless run must produce all
    four outputs and never enter the interactive chat loop.
    """
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)
    toc_path = output_dir / config_loader.get("system.toc_filename", "ToC.json")

    async def fake_generate_toc(model=None):
        write_valid_toc(toc_path)

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


def test_headless_exits_nonzero_when_outputs_missing(monkeypatch, tmp_path, write_valid_toc):
    """--headless must exit 1 when the audit leaves outputs missing."""
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)

    async def fake_generate_toc(model=None):
        write_valid_toc(output_dir / config_loader.get("system.toc_filename", "ToC.json"))

    monkeypatch.setattr(app, "generate_toc", fake_generate_toc)

    # Force the pre-chat audit to fail so outputs stay missing.
    async def broken_prechat(*a, **k):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(app, "build_prechat_audit_agent", broken_prechat)

    monkeypatch.setattr(sys, "argv", ["main.py", "-m", "mock", "--headless", "--no-rich"])

    with pytest.raises(SystemExit) as exc:
        asyncio.run(app.main())
    assert exc.value.code == 1


def test_headless_exits_nonzero_when_prechat_raises_and_outputs_exist(monkeypatch, tmp_path, write_valid_toc):
    """A raised pre-chat failure must exit 1 even if outputs already exist.

    The missing-output gate already exits 1 when files are absent. This test
    locks the other hole: --coordinator-only runs the audit, the runner
    raises, and stale outputs must not turn that failure into exit 0.
    """
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)
    write_valid_toc(output_dir / config_loader.get("system.toc_filename", "ToC.json"))
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
    # The report is set aside before synthesis, so a failed run leaves it missing (never stale
    # and never overwritten with the error); the previous text survives as .prev.
    assert not report_path.exists()
    prev = report_path.with_name(report_path.name + ".prev")
    assert prev.read_text(encoding="utf-8") == report_text
    assert "TOKEN_422_SYNTHETIC" not in prev.read_text(encoding="utf-8")
    assert "Error calling OpenRouter:" not in prev.read_text(encoding="utf-8")



# --- Validated reuse and the trustworthy-completion gate (Tactical 3) ---
from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm, LlmResponse
from google.genai import types

ARTIFACTS = ("permissions_agent.md", "constraints_agent.md", "boundaries_agent.md")


def _seed(monkeypatch, tmp_path, write_valid_toc, artifacts=None, report="old report\n"):
    """Valid ToC plus the given artifact contents (name -> text; default all valid)."""
    output_dir = _isolate_output_dirs(monkeypatch, tmp_path)
    write_valid_toc(output_dir / config_loader.get("system.toc_filename", "ToC.json"))
    artifacts = artifacts if artifacts is not None else {n: f"valid {n}\n" for n in ARTIFACTS}
    for name, text in artifacts.items():
        (output_dir / "artifacts" / name).write_text(text, encoding="utf-8")
    if report is not None:
        (output_dir / "reports" / "Security_Threat_Model.md").write_text(report, encoding="utf-8")
    return output_dir


def _run(monkeypatch, *flags):
    monkeypatch.setattr(sys, "argv", ["main.py", "-m", "mock", "--no-rich", *flags])
    asyncio.run(app.main())


def _forbid_model_calls(monkeypatch):
    async def boom(*_a, **_k):  # pragma: no cover - must not run
        raise AssertionError("no model/pre-chat run expected")

    monkeypatch.setattr(app.RichUI, "stream_response", boom)


def test_empty_artifact_is_regenerated_others_replayed(monkeypatch, tmp_path, write_valid_toc):
    out = _seed(monkeypatch, tmp_path, write_valid_toc, artifacts={
        "permissions_agent.md": "  \n",
        "constraints_agent.md": "valid constraints\n",
        "boundaries_agent.md": "valid boundaries\n",
    })
    _run(monkeypatch, "--headless")
    assert "# RBAC Analysis" in (out / "artifacts" / "permissions_agent.md").read_text(encoding="utf-8")
    assert (out / "artifacts" / "constraints_agent.md").read_text(encoding="utf-8") == "valid constraints\n"
    assert "Master Audit Report" in (out / "reports" / "Security_Threat_Model.md").read_text(encoding="utf-8")


def test_legacy_skipped_artifact_is_regenerated(monkeypatch, tmp_path, write_valid_toc):
    out = _seed(monkeypatch, tmp_path, write_valid_toc, artifacts={
        "permissions_agent.md": "valid\n",
        "constraints_agent.md": "SKIPPED: constraints_agent was skipped because --coordinator-only\n",
        "boundaries_agent.md": "valid\n",
    })
    _run(monkeypatch, "--headless")
    text = (out / "artifacts" / "constraints_agent.md").read_text(encoding="utf-8")
    assert "SKIPPED" not in text and "Logic Analysis" in text


def _tree(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_coordinator_only_with_skipped_artifact_exits_1_and_touches_nothing(monkeypatch, tmp_path, write_valid_toc):
    out = _seed(monkeypatch, tmp_path, write_valid_toc, artifacts={
        "permissions_agent.md": "valid\n",
        "constraints_agent.md": "SKIPPED: x\n",
        "boundaries_agent.md": "valid\n",
    })
    before = _tree(out)
    _forbid_model_calls(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "--headless", "--coordinator-only")
    assert exc.value.code == 1
    assert _tree(out) == before


def test_coordinator_only_with_missing_artifact_exits_1_and_writes_no_placeholder(monkeypatch, tmp_path, write_valid_toc):
    out = _seed(monkeypatch, tmp_path, write_valid_toc, artifacts={
        "permissions_agent.md": "valid\n",
        "boundaries_agent.md": "valid\n",
    })
    _forbid_model_calls(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "--headless", "--coordinator-only")
    assert exc.value.code == 1
    assert not (out / "artifacts" / "constraints_agent.md").exists()
    assert "SKIPPED" not in "".join(p.read_text(encoding="utf-8") for p in (out / "artifacts").iterdir())


class _SilentModel(BaseLlm):
    """Ends the turn with text and never calls a tool, so no file gets written."""
    model: str = "silent"

    async def generate_content_async(self, request, stream=False):
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part.from_text(text="done")]))


def test_synthesis_that_writes_no_report_exits_1_and_keeps_old_report_as_prev(monkeypatch, tmp_path, write_valid_toc):
    out = _seed(monkeypatch, tmp_path, write_valid_toc, report="old report text\n")
    monkeypatch.setattr(
        app, "create_coordinator_synthesizer",
        lambda provider=None, model=None: LlmAgent(name="coordinator_psa", model=_SilentModel()),
    )
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "--headless", "--coordinator-only")
    assert exc.value.code == 1
    report = out / "reports" / "Security_Threat_Model.md"
    assert not report.exists()
    assert report.with_name(report.name + ".prev").read_text(encoding="utf-8") == "old report text\n"


def test_all_valid_nothing_to_do_reports_every_output_reused(monkeypatch, tmp_path, write_valid_toc, capsys):
    out = _seed(monkeypatch, tmp_path, write_valid_toc)
    before = {p.name: p.read_text(encoding="utf-8") for p in (out / "artifacts").iterdir()}
    _forbid_model_calls(monkeypatch)
    _run(monkeypatch, "--headless")
    printed = capsys.readouterr().out
    assert printed.count("(reused)") == 4 and "(generated)" not in printed
    assert {p.name: p.read_text(encoding="utf-8") for p in (out / "artifacts").iterdir()} == before
