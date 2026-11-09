"""Unit tests for sdaa.src.core.output_validation (D3 rules and set_aside)."""
import json
import os

import pytest

from sdaa.src.core import output_validation as ov
from sdaa.src.tools import file_ops


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.md").write_text("# a", encoding="utf-8")
    (root / "b.md").write_text("# b", encoding="utf-8")
    monkeypatch.setattr(file_ops, "_get_docs_root", lambda: str(root))
    return root


def _entry(path, summary="A summary.", tags=("x", "y", "z")):
    return {"path": path, "summary": summary, "tags": list(tags)}


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_valid_toc(corpus, tmp_path):
    toc = _write(tmp_path / "toc.json", {"files": [_entry("a.md"), _entry("b.md")]})
    assert ov.toc_problems(toc) == []


def test_toc_missing(corpus, tmp_path):
    assert ov.toc_problems(str(tmp_path / "nope.json"))


def test_toc_not_json(corpus, tmp_path):
    p = tmp_path / "toc.json"
    p.write_text("not json", encoding="utf-8")
    assert ov.toc_problems(str(p))


@pytest.mark.parametrize("data", [{}, {"files": []}, {"files": "x"}, [], {"files": [1]}])
def test_toc_bad_shape(corpus, tmp_path, data):
    assert ov.toc_problems(_write(tmp_path / "toc.json", data))


@pytest.mark.parametrize(
    "entry",
    [
        {"summary": "s", "tags": ["a", "b", "c"]},                        # no path
        {"path": "a.md", "tags": ["a", "b", "c"]},                         # no summary
        {"path": "a.md", "summary": "s"},                                  # no tags
        _entry("a.md", summary="   "),                                     # blank summary
        _entry("a.md", tags=("x", "y")),                                   # 2 tags
        _entry("a.md", tags=("x", "y", "")),                               # blank tag
        _entry("a.md", summary="Error reading file: boom"),                # legacy swallowed error
    ],
)
def test_toc_bad_entry(corpus, tmp_path, entry):
    assert ov.toc_problems(_write(tmp_path / "toc.json", {"files": [entry]}))


def test_toc_path_not_in_corpus(corpus, tmp_path):
    assert ov.toc_problems(_write(tmp_path / "toc.json", {"files": [_entry("ghost.md")]}))


def test_toc_dotdot_path_rejected(corpus, tmp_path):
    (tmp_path / "outside.md").write_text("x", encoding="utf-8")
    assert ov.toc_problems(_write(tmp_path / "toc.json", {"files": [_entry("../outside.md")]}))


def test_toc_absolute_path_rejected(corpus, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    assert ov.toc_problems(_write(tmp_path / "toc.json", {"files": [_entry(str(outside))]}))


def test_toc_symlink_escape_rejected(corpus, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    os.symlink(outside, corpus / "link.md")
    assert ov.toc_problems(_write(tmp_path / "toc.json", {"files": [_entry("link.md")]}))


def test_toc_duplicate_paths(corpus, tmp_path):
    assert ov.toc_problems(_write(tmp_path / "toc.json", {"files": [_entry("a.md"), _entry("a.md")]}))


def test_text_output_valid(tmp_path):
    p = tmp_path / "f.md"
    p.write_text("# findings", encoding="utf-8")
    assert ov.text_output_problems(str(p)) == []


@pytest.mark.parametrize("content", ["", "  \n\t\n", "SKIPPED: x was skipped", "\n  SKIPPED: x"])
def test_text_output_invalid_content(tmp_path, content):
    p = tmp_path / "f.md"
    p.write_text(content, encoding="utf-8")
    assert ov.text_output_problems(str(p))


def test_text_output_missing_and_directory(tmp_path):
    assert ov.text_output_problems(str(tmp_path / "nope.md"))
    assert ov.text_output_problems(str(tmp_path))


def test_text_output_not_utf8(tmp_path):
    p = tmp_path / "f.md"
    p.write_bytes(b"\xff\xfe\x00bad")
    assert ov.text_output_problems(str(p))


def test_audit_output_paths_and_problems():
    paths = ov.audit_output_paths()
    assert [os.path.basename(p) for p in paths] == [
        "permissions_agent.md", "constraints_agent.md", "boundaries_agent.md", ov.REPORT_FILENAME,
    ]
    assert len(ov.audit_output_problems()) == 4  # nothing written yet
    for p in paths:
        with open(p, "w", encoding="utf-8") as f:
            f.write("ok")
    assert ov.audit_output_problems() == []


def test_set_aside_moves_ignores_missing_and_overwrites_prev(tmp_path):
    a, missing = tmp_path / "a.md", tmp_path / "missing.md"
    a.write_text("new", encoding="utf-8")
    (tmp_path / "a.md.prev").write_text("older", encoding="utf-8")
    ov.set_aside([str(a), str(missing)])
    assert not a.exists()
    assert (tmp_path / "a.md.prev").read_text(encoding="utf-8") == "new"
    assert not (tmp_path / "missing.md.prev").exists()
