import asyncio
import json
import re
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import main as app
from tests.test_main_headless import _real_paths, _STUB_PROMPTS
from sdaa.src.utils.prompt_manager import prompt_manager


def _prompt(name):
    if name not in _STUB_PROMPTS:
        return None
    return SimpleNamespace(name=name, version=7, compile=lambda **kwargs: _STUB_PROMPTS[name])


@pytest.fixture(autouse=True)
def _stub_prompts(monkeypatch):
    monkeypatch.setattr(prompt_manager, "get_prompt_object", lambda name, **kwargs: _prompt(name))


def _paths(monkeypatch, tmp_path):
    _real_paths(monkeypatch)
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "auth.md").write_text("# Auth\nAdmins can manage users.\n", encoding="utf-8")
    (corpus / "billing.md").write_text("# Billing\nViewers cannot edit invoices.\n", encoding="utf-8")
    return corpus, tmp_path / "run_output"


def _run(monkeypatch, corpus, output, *flags, headless=True):
    argv = ["main.py", "-m", "mock", "--no-rich", "--docs-root", str(corpus),
            "--output-dir", str(output)]
    if headless:
        argv.append("--headless")
    monkeypatch.setattr(sys, "argv", argv + list(flags))
    asyncio.run(app.main())


def _manifest(output):
    return json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))


def test_m1_tree_hash(tmp_path):
    from sdaa.src.core.run_manifest import tree_hash

    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    files = {"b.md": b"b", "a.md": b"a", ".hidden": b"hidden", "data.bin": b"\x00"}
    for name in files:
        (first / name).write_bytes(files[name])
    for name in reversed(files):
        (second / name).write_bytes(files[name])
    (first / "empty").mkdir()
    (first / "linked.md").symlink_to(second / "a.md")
    (first / "linked_dir").symlink_to(second, target_is_directory=True)
    assert tree_hash(str(first)) == tree_hash(str(second))
    assert tree_hash(str(first))[1] == 4
    original = tree_hash(str(first))
    assert tree_hash(str(first)) == original
    (first / "a.md").write_bytes(b"A")
    assert tree_hash(str(first))[0] != original[0]


def test_m2_full_mock_manifest(monkeypatch, tmp_path):
    from sdaa.src.core.run_manifest import tree_hash

    corpus, output = _paths(monkeypatch, tmp_path)
    instrumentation = Mock(wraps=app.setup_instrumentation)
    session = AsyncMock(wraps=app.InMemorySessionService.create_session)
    monkeypatch.setattr(app, "setup_instrumentation", instrumentation)
    # Bind the original method explicitly: AsyncMock on a class is not a descriptor.

    async def create_session(service, **kwargs):
        return await session(service, **kwargs)

    monkeypatch.setattr(app.InMemorySessionService, "create_session", create_session)
    _run(monkeypatch, corpus, output, "--run-id", "t-m2")
    manifest = _manifest(output)
    assert set(manifest) == {
        "schema", "run_id", "started_at", "ended_at", "argv", "provider", "paths",
        "code", "corpus", "agents", "usage", "outputs", "outcome", "calls",
    }
    assert manifest["schema"] == 1
    assert manifest["run_id"] == "t-m2"
    assert manifest["outcome"] == {"exit_code": 0, "problems": []}
    assert len(manifest["outputs"]) == 5
    for value in manifest["outputs"].values():
        assert value["status"] == "generated"
        assert re.fullmatch("[0-9a-f]{64}", value["sha256"])
    assert set(manifest["agents"]) == {
        "map_maker", "permissions_agent", "constraints_agent", "boundaries_agent", "coordinator",
    }
    for agent, prompt in (
        ("permissions_agent", "permissions-agent"),
        ("constraints_agent", "negative-constraints-agent"),
        ("boundaries_agent", "security-boundaries-agent"),
        ("coordinator", "report-synthesizer"),
    ):
        assert manifest["agents"][agent]["calls"] >= 1
        assert manifest["agents"][agent]["prompts"] == [{"name": prompt, "version": 7}]
    assert manifest["agents"]["map_maker"]["calls"] >= 1
    assert manifest["agents"]["map_maker"]["prompts"] == [{"name": None, "version": None}]
    assert manifest["usage"]["cost_usd"] == 0.0
    assert manifest["usage"]["unmetered_calls"] == 0
    digest, count = tree_hash(str(corpus))
    assert manifest["corpus"] == {"tree_hash": digest, "file_count": count}
    assert count == 2
    instrumentation.assert_called_once_with(session_id="t-m2")
    assert session.await_count == 1
    assert session.await_args.kwargs["session_id"] == "t-m2"


def test_m3_prechat_failure(monkeypatch, tmp_path):
    corpus, output = _paths(monkeypatch, tmp_path)

    async def broken_prechat(**kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(app, "build_prechat_audit_agent", broken_prechat)
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, corpus, output)
    assert exc.value.code == 1
    assert _manifest(output)["outcome"]["exit_code"] == 1
    assert _manifest(output)["outcome"]["problems"]


def test_m4_missing_prompt(monkeypatch, tmp_path):
    corpus, output = _paths(monkeypatch, tmp_path)
    monkeypatch.setattr(prompt_manager, "get_prompt_object",
                        lambda name, **kwargs: None if name == "negative-constraints-agent" else _prompt(name))
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, corpus, output)
    assert exc.value.code == 1
    agents = _manifest(output)["agents"]
    assert agents["constraints_agent"]["prompts"] == [{"name": None, "version": None}]
    for agent, name in (("permissions_agent", "permissions-agent"),
                        ("boundaries_agent", "security-boundaries-agent"),
                        ("coordinator", "report-synthesizer")):
        assert agents[agent]["prompts"] == [{"name": name, "version": 7}]


def test_m5_invalid_run_id(monkeypatch, tmp_path, capsys):
    corpus, output = _paths(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, corpus, output, "--run-id", "../x")
    assert exc.value.code == 2
    assert "use 1-64 letters" in capsys.readouterr().err
    assert not (output / "run_manifest.json").exists()


def test_m6_second_run_reuses_outputs(monkeypatch, tmp_path):
    corpus, output = _paths(monkeypatch, tmp_path)
    _run(monkeypatch, corpus, output)
    assert _manifest(output)["usage"]["calls"] > 0
    _run(monkeypatch, corpus, output)
    manifest = _manifest(output)
    assert all(value["status"] == "reused" for value in manifest["outputs"].values())
    assert manifest["usage"]["calls"] == 0


def test_m7_generated_id_and_no_interactive_manifest(monkeypatch, tmp_path):
    corpus, output = _paths(monkeypatch, tmp_path)
    _run(monkeypatch, corpus, output)
    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{6}", _manifest(output)["run_id"])
    interactive_output = tmp_path / "interactive_output"
    _run(monkeypatch, corpus, interactive_output, "--toc-only", headless=False)
    assert not (interactive_output / "run_manifest.json").exists()


def test_m8_coordinator_only_reuses_artifacts(monkeypatch, tmp_path, capsys):
    corpus, output = _paths(monkeypatch, tmp_path)
    _run(monkeypatch, corpus, output)
    capsys.readouterr()
    _run(monkeypatch, corpus, output, "--coordinator-only")
    outputs = _manifest(output)["outputs"]
    for name in ("ToC.json", "permissions_agent.md", "constraints_agent.md", "boundaries_agent.md"):
        assert outputs[name]["status"] == "reused"
    assert outputs["Security_Threat_Model.md"]["status"] == "generated"
    printed = capsys.readouterr().out
    for name, value in outputs.items():
        if name != "ToC.json":
            assert f"{name} ({value['status']})" in printed


def test_m9_uncaught_exception(monkeypatch, tmp_path):
    corpus, output = _paths(monkeypatch, tmp_path)
    monkeypatch.setattr(app, "create_coordinator_agent", Mock(side_effect=RuntimeError("coordinator failed")))
    with pytest.raises(RuntimeError, match="coordinator failed"):
        _run(monkeypatch, corpus, output)
    assert _manifest(output)["outcome"]["exit_code"] == 1


def test_m10_headless_toc_only(monkeypatch, tmp_path):
    corpus, output = _paths(monkeypatch, tmp_path)
    _run(monkeypatch, corpus, output, "--toc-only")
    manifest = _manifest(output)
    assert manifest["outcome"] == {"exit_code": 0, "problems": []}
    assert manifest["outputs"]["ToC.json"]["status"] == "generated"
    audit_outputs = [value for name, value in manifest["outputs"].items() if name != "ToC.json"]
    assert len(audit_outputs) == 4
    assert all(value == {"status": "missing", "sha256": None} for value in audit_outputs)


def test_c1_synthesizer_clears_stale_prompt(monkeypatch):
    from sdaa.src.agents.coordinator import create_coordinator_synthesizer
    from sdaa.src.utils.mock_model import MockModel

    model = MockModel()
    agent = create_coordinator_synthesizer(model=model)
    assert "Principal Security Architect" in agent.instruction(None)
    assert model._langfuse_prompt.version == 7
    monkeypatch.setattr(prompt_manager, "get_prompt_object", lambda **kwargs: None)
    assert agent.instruction(None).startswith("Error:")
    assert model._langfuse_prompt is None
