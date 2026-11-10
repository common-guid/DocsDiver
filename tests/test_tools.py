import os
import pytest
from pathlib import Path

from sdaa.src.tools.file_ops import read_file, list_files, resolve_corpus_path
from sdaa.src.core import config_loader as config_loader_mod


# ---------------------------------------------------------------------------
# Existing tests (run against the real docs-for-testing/ corpus)
# ---------------------------------------------------------------------------

def test_read_file_safe():
    # Setup docs-for-testing/auth.md exists
    content = read_file("auth.md")
    assert "Authentication" in content


def test_read_file_traversal():
    # T1: tools return an error string (not raise) so the model can recover.
    result = read_file("../requirements.txt")
    assert result.startswith("Error: Access denied:")
    assert "outside the documentation root or uses a symlink" in result


def test_list_files():
    files = list_files()
    assert "auth.md" in files
    assert "billing.md" in files


# ---------------------------------------------------------------------------
# T1 security and determinism tests (use an isolated temporary corpus)
# ---------------------------------------------------------------------------

@pytest.fixture

def tmp_corpus(tmp_path, monkeypatch):
    """Build a controlled corpus layout and patch docs_root + output_dir.

    Layout:
      <tmp>/corpus/
        a.md
        sub/b.md
        z.md
      <tmp>/corpus-private/secret.md
      <tmp>/outside/creds
    """
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.md").write_text("# a\ncontent a", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub/b.md").write_text("# b\ncontent b", encoding="utf-8")
    (root / "z.md").write_text("# z\ncontent z", encoding="utf-8")

    # sibling private dir
    private = tmp_path / "corpus-private"
    private.mkdir()
    (private / "secret.md").write_text("SENSITIVE", encoding="utf-8")

    # outside
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "creds").write_text("CREDS", encoding="utf-8")

    # Patch the module-level lookup used by file_ops and callers.
    monkeypatch.setattr("sdaa.src.tools.file_ops._get_docs_root", lambda: str(root))
    # Also patch the config_loader singleton method for any ToC basename tests.
    monkeypatch.setattr(config_loader_mod.config_loader, "get_output_dir", lambda: str(tmp_path / "output"))

    # Ensure output dir exists for ToC tests
    (tmp_path / "output").mkdir(exist_ok=True)

    return root


def test_read_file_nested_and_absolute(tmp_corpus):
    assert "content a" in read_file("a.md")
    assert "content b" in read_file("sub/b.md")
    # absolute inside the root
    abs_inside = str(tmp_corpus / "sub/b.md")
    assert "content b" in read_file(abs_inside)


def test_read_file_sibling_prefix_denied_string_and_logs(tmp_corpus, caplog, tmp_path):
    caplog.set_level("WARNING")
    for bad in ("../corpus-private/secret.md", str(tmp_path / "corpus-private/secret.md")):
        result = read_file(bad)
        assert result.startswith("Error: Access denied:")
        assert "outside the documentation root or uses a symlink" in result
    # At least one warning for the relative case (absolute also triggers)
    assert any("Access denied" in r.message for r in caplog.records)


def test_read_file_plain_traversal_and_absolute_outside(tmp_corpus, tmp_path):
    assert read_file("../outside/creds").startswith("Error: Access denied:")
    abs_out = str(tmp_path / "outside/creds")
    assert read_file(abs_out).startswith("Error: Access denied:")


def test_read_file_symlink_file_denied(tmp_corpus, tmp_path):
    # symlink file -> outside
    outside_file = tmp_path / "outside/creds"
    link_out = tmp_corpus / "leak.md"
    os.symlink(outside_file, link_out)
    assert read_file("leak.md").startswith("Error: Access denied:")

    # symlink file -> inside the corpus (still denied per D2)
    inside_target = tmp_corpus / "a.md"
    link_in = tmp_corpus / "alias.md"
    os.symlink(inside_target, link_in)
    assert read_file("alias.md").startswith("Error: Access denied:")


def test_read_file_symlink_directory_denied(tmp_corpus, tmp_path):
    outside = tmp_path / "outside"
    linkdir = tmp_corpus / "linkdir"
    os.symlink(outside, linkdir)
    assert read_file("linkdir/creds").startswith("Error: Access denied:")


def test_resolve_corpus_path_raises_on_escapes(tmp_corpus, tmp_path):
    with pytest.raises(ValueError):
        resolve_corpus_path("../corpus-private/secret.md")
    with pytest.raises(ValueError):
        resolve_corpus_path(str(tmp_path / "outside/creds"))
    # symlink file
    os.symlink(tmp_path / "outside/creds", tmp_corpus / "l.md")
    with pytest.raises(ValueError):
        resolve_corpus_path("l.md")


def test_denial_message_contains_requested_not_resolved(tmp_corpus):
    result = read_file("../corpus-private/secret.md")
    assert "../corpus-private/secret.md" in result
    assert str(tmp_corpus) not in result  # do not leak resolved absolute


def test_linkdir_dotdot_is_resolved_safely(tmp_corpus, tmp_path):
    # linkdir/../a.md lexical-collapses to a.md (root-level file), proving we open the *returned* resolved path
    # and do not follow the symlink for the .. segment.
    linkdir = tmp_corpus / "linkdir"
    os.symlink(tmp_corpus / "sub", linkdir)
    content = read_file("linkdir/../a.md")
    assert "content a" in content


def test_list_files_sibling_denied(tmp_corpus):
    assert list_files("../corpus-private").startswith("Error: Access denied:")


def test_list_files_skips_symlinks_and_sorts_and_warns(tmp_corpus, caplog):
    caplog.set_level("WARNING")
    # create a symlinked file and a symlinked directory inside the corpus
    os.symlink(tmp_corpus / "a.md", tmp_corpus / "symfile.md")
    os.symlink(tmp_corpus / "sub", tmp_corpus / "symdir")
    # also create a normal file after z to test global sort
    (tmp_corpus / "m.md").write_text("# m", encoding="utf-8")

    listing = list_files()
    paths = [p for p in listing.splitlines() if p]  # non-empty
    assert paths == sorted(paths)
    assert "a.md" in paths
    assert "sub/b.md" in paths
    assert "z.md" in paths
    assert "m.md" in paths
    # symlinked entries must NOT appear
    assert "symfile.md" not in paths
    assert not any(p.startswith("symdir") for p in paths)
    # one warning per skipped symlink
    warnings = [r for r in caplog.records if "symlink" in r.message.lower() or "Access denied" in r.message]
    assert len(warnings) >= 2


def test_read_file_toc_by_exact_name(tmp_corpus, tmp_path):
    toc_path = tmp_path / "output" / "ToC.json"
    toc_path.write_text('{"files": [{"path": "a.md", "summary": "s", "tags": ["x","y","z"]}]}', encoding="utf-8")
    content = read_file("ToC.json")
    assert "a.md" in content


def test_read_file_toc_subpath_or_outside_not_redirected(tmp_corpus, tmp_path):
    # sub/ToC.json should be treated as a normal corpus path (not found)
    result = read_file("sub/ToC.json")
    assert result.startswith("Error: File not found:")

    # outside path with ToC basename must be denied, not redirected
    result2 = read_file("../../x/ToC.json")
    assert result2.startswith("Error: Access denied:")


def test_read_file_missing_and_list_missing(tmp_corpus):
    assert read_file("nope.md").startswith("Error: File not found:")
    assert list_files("no_such_dir").startswith("Error: Directory not found:")
