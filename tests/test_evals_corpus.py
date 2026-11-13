from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from evals import corpus, key
from sdaa.src.core import run_manifest

EXAMPLE = Path(__file__).resolve().parents[1] / "evals" / "examples" / "acme"
ROOT = EXAMPLE.parents[2]


def _copy(tmp_path):
    return Path(shutil.copytree(EXAMPLE / "clean", tmp_path / "clean"))


def _edits():
    return key.approved_edits(key.load(EXAMPLE / "key.yaml"))


def _cli(*args):
    return subprocess.run([sys.executable, "-m", "evals", *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True)


def test_example_verify():
    clean = EXAMPLE / "clean"
    assert corpus.verify(clean) == []
    assert corpus.tree_hash is run_manifest.tree_hash
    assert corpus.tree_hash(clean) == run_manifest.tree_hash(clean)
    digest, count = corpus.tree_hash(clean)
    result = _cli("corpus", "verify", clean)
    assert result.returncode == 0
    assert result.stdout == f"OK {count} files, tree {digest}\n"
    assert result.stderr == ""


@pytest.mark.parametrize("case,expected", [
    ("file-link", "symlink: alias.md"),
    ("dir-link", "symlink: alias"),
    ("notes.txt", "non-Markdown file: notes.txt"),
    (".DS_Store", "non-Markdown file: .DS_Store"),
    ("duplicate", "duplicate bytes: admin/roles.md, duplicate.md"),
    ("empty", "no .md files"),
    ("missing", "root missing or not a directory"),
    ("file-root", "root missing or not a directory"),
])
def test_verify_rejections(tmp_path, case, expected):
    clean = _copy(tmp_path)
    if case == "file-link":
        (clean / "alias.md").symlink_to(clean / "admin/roles.md")
    elif case == "dir-link":
        (clean / "alias").symlink_to(clean / "admin", target_is_directory=True)
    elif case == "duplicate":
        shutil.copyfile(clean / "admin/roles.md", clean / "duplicate.md")
    elif case in ("empty", "missing", "file-root"):
        clean = tmp_path / case
        if case == "empty":
            clean.mkdir()
        elif case == "file-root":
            clean.write_bytes(b"not a directory")
    else:
        (clean / case).write_bytes(b"extra")
    assert corpus.verify(clean) == [expected]


def test_sections_ignore_fenced_comment():
    text = (EXAMPLE / "clean/api/tokens.md").read_text()
    assert corpus.section_at(text, text.index("curl")) == "Creating a token"
    assert corpus.section_at(text, text.index("Tokens expire")) == "Expiry"
    assert corpus.section_at(text, 0) == ""
    assert "List the notebooks you can see" not in corpus.headings(text)
    assert corpus.headings("   ## Name ###\n~~~sh\n# hidden\n~~~\n# End\n") == ["Name", "End"]
    assert corpus.section_at("# First\n## Second\n", len("# First\n")) == "First"


def test_cli_build_reproducible(tmp_path):
    records = []
    for index in range(2):
        seeded = tmp_path / f"output-{index}"
        variants = tmp_path / f"variants-{index}.yaml"
        result = _cli("corpus", "build", "--key", EXAMPLE / "key.yaml",
                      "--clean", EXAMPLE / "clean", "--seeded", seeded, "--variants", variants)
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        record = yaml.safe_load(variants.read_bytes())
        assert record["plants"] == ["PL-01"]
        assert record["key_hash"] == key.key_hash(EXAMPLE / "key.yaml")
        assert record["snapshot_id"] == "acme-2026-01-01"
        assert record["key_id"] == "acme-example"
        assert record["variants"]["seeded"]["files"] == 4
        assert result.stdout == (
            f"OK clean {record['variants']['clean']['tree_hash']} "
            f"seeded {record['variants']['seeded']['tree_hash']}, 1 plants -> {variants}\n")
        records.append(variants.read_bytes())
    assert records[0] == records[1]
    assert corpus.tree_hash(tmp_path / "output-0") == corpus.tree_hash(tmp_path / "output-1")


def test_build_only_approved_edit(tmp_path):
    clean, seeded = EXAMPLE / "clean", tmp_path / "seeded"
    result = corpus.build(clean, seeded, _edits())
    before = {p.relative_to(clean).as_posix(): p.read_bytes() for p in clean.rglob("*.md")}
    after = {p.relative_to(seeded).as_posix(): p.read_bytes() for p in seeded.rglob("*.md")}
    assert before.keys() == after.keys()
    assert [p for p in before if before[p] != after[p]] == ["sharing/links.md"]
    _, path, find, replace = _edits()[0]
    assert replace.encode() in after[path] and find.encode() not in after[path]
    draft = key.load(EXAMPLE / "key.yaml")["items"][1]["plant"][0]["replace"]
    assert draft.encode() not in after["api/tokens.md"]
    assert result["clean"]["tree_hash"] != result["seeded"]["tree_hash"]
    for name, root in (("clean", clean), ("seeded", seeded)):
        digest, count = run_manifest.tree_hash(root)
        assert result[name] == {"tree_hash": digest, "files": count}


@pytest.mark.parametrize("count,detail", [(0, "zero occurrences"), (2, "two-or-more occurrences")])
def test_build_find_count(tmp_path, count, detail):
    clean = _copy(tmp_path)
    edits = _edits()
    item_id, path, find, replace = edits[0]
    if count == 0:
        edits = [(item_id, path, "absent sentence", replace)]
    else:
        page = clean / path
        page.write_bytes(page.read_bytes() + b"\n" + find.encode())
    seeded = tmp_path / "seeded"
    with pytest.raises(corpus.CorpusError) as caught:
        corpus.build(clean, seeded, edits)
    assert caught.value.problems == [f"{item_id}: {path}: find has {detail}"]
    assert str(caught.value) == "\n".join(caught.value.problems)
    assert not seeded.exists()


def test_overlapping_edits(tmp_path):
    path = "sharing/links.md"
    edits = [("PL-01", path, "Only Admins can create", "X"),
             ("PL-02", path, "Admins can create public", "Y")]
    with pytest.raises(corpus.CorpusError, match="overlapping"):
        corpus.build(EXAMPLE / "clean", tmp_path / "seeded", edits)
    assert not (tmp_path / "seeded").exists()


def test_touching_edits(tmp_path):
    # The first replacement changes length, so applying edits front to back would corrupt the second.
    edits = [("PL-01", "sharing/links.md", "Only Admins", "Every Editor"),
             ("PL-02", "sharing/links.md", " can create public links.", " may publish.")]
    corpus.build(EXAMPLE / "clean", tmp_path / "seeded", edits)
    assert b"Every Editor may publish. Public links" in (tmp_path / "seeded/sharing/links.md").read_bytes()


def test_unknown_edit_path_and_collect_all(tmp_path):
    with pytest.raises(corpus.CorpusError) as caught:
        corpus.build(EXAMPLE / "clean", tmp_path / "seeded",
                     [("PL-01", "../outside.md", "a", "b"),
                      ("PL-02", "missing.md", "c", "d")])
    assert len(caught.value.problems) == 2
    assert caught.value.problems[0].startswith("PL-01: ../outside.md:")
    assert caught.value.problems[1].startswith("PL-02: missing.md:")
    assert not (tmp_path / "seeded").exists()


@pytest.mark.parametrize("target", ["exists", "equal", "inside", "contains"])
def test_build_refuses_target(tmp_path, target):
    clean = _copy(tmp_path)
    seeded = tmp_path / "seeded"
    if target == "exists":
        seeded.mkdir()
        (seeded / "sentinel").write_bytes(b"keep")
    elif target == "equal":
        seeded = clean
    elif target == "inside":
        seeded = clean / "nested"
    else:
        seeded = tmp_path
    with pytest.raises(corpus.CorpusError):
        corpus.build(clean, seeded, _edits())
    if target == "exists":
        assert (seeded / "sentinel").read_bytes() == b"keep"
    if target == "inside":
        assert not seeded.exists()


def test_crlf_survives(tmp_path):
    clean = _copy(tmp_path)
    for relative in ("admin/roles.md", "sharing/links.md"):
        path = clean / relative
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    seeded = tmp_path / "seeded"
    corpus.build(clean, seeded, _edits())
    assert (seeded / "admin/roles.md").read_bytes() == (clean / "admin/roles.md").read_bytes()
    edited = (seeded / "sharing/links.md").read_bytes()
    assert b"\r\n" in edited
    assert b"\n" not in edited.replace(b"\r\n", b"")
    assert _edits()[0][3].encode() in edited


def test_build_invalid_utf8(tmp_path):
    clean = _copy(tmp_path)
    (clean / "api/tokens.md").write_bytes(b"\xff")
    with pytest.raises(corpus.CorpusError, match="UTF-8"):
        corpus.build(clean, tmp_path / "seeded", _edits())
    assert not (tmp_path / "seeded").exists()


def test_build_rejects_unsafe_corpus(tmp_path):
    clean = _copy(tmp_path)
    (clean / "alias.md").symlink_to(clean / "admin/roles.md")
    with pytest.raises(corpus.CorpusError, match="symlink"):
        corpus.build(clean, tmp_path / "seeded", [])
    assert not (tmp_path / "seeded").exists()
