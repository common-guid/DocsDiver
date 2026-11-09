import pytest
from sdaa.src.core.map_maker import generate_toc
from sdaa.src.core.config_loader import config_loader
import os
import json

@pytest.mark.asyncio
async def test_generate_toc():
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")
    output_dir = config_loader.get_output_dir()
    toc_path = os.path.join(output_dir, toc_filename)

    # conftest gives each test a fresh output dir, so no pre-existing ToC can trigger the skip guard.
    assert not os.path.exists(toc_path)

    # Run async function
    await generate_toc()

    # Check ToC.json exists at the resolved output path
    assert os.path.exists(toc_path)

    with open(toc_path) as f:
        data = json.load(f)
        assert "files" in data
        assert len(data["files"]) > 0

        # Verify summary and tags format (MockModel logic)
        first = data["files"][0]
        assert "path" in first
        assert "summary" in first
        assert "tags" in first
        assert isinstance(first["tags"], list)
        assert len(first["tags"]) == 3
        assert all(isinstance(t, str) for t in first["tags"])
        # MockModel returns mock summary or logic based on content


# --- Failure propagation (Tactical 3, D6): Map Maker must raise, never index error text ---
import asyncio

from sdaa.src.core.output_validation import toc_problems
from sdaa.src.tools import file_ops


@pytest.fixture
def tmp_corpus(tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setattr(file_ops, "_get_docs_root", lambda: str(root))
    return root


def _toc_path():
    return os.path.join(config_loader.get_output_dir(), config_loader.get("system.toc_filename", "ToC.json"))


def test_generate_toc_happy_path_is_valid(tmp_corpus):
    (tmp_corpus / "a.md").write_text("# a", encoding="utf-8")
    asyncio.run(generate_toc())
    assert toc_problems(_toc_path()) == []


def test_generate_toc_empty_corpus_raises_and_writes_nothing(tmp_corpus):
    with pytest.raises(ValueError, match="no Markdown files"):
        asyncio.run(generate_toc())
    assert not os.path.exists(_toc_path())


def test_generate_toc_missing_docs_root_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(file_ops, "_get_docs_root", lambda: str(tmp_path / "gone"))
    with pytest.raises(FileNotFoundError):
        asyncio.run(generate_toc())
    assert not os.path.exists(_toc_path())


def test_generate_toc_unreadable_doc_raises_naming_file(tmp_corpus):
    (tmp_corpus / "good.md").write_text("# ok", encoding="utf-8")
    (tmp_corpus / "bad.md").write_bytes(b"\xff\xfe\x00not utf8")
    with pytest.raises(RuntimeError, match="bad.md"):
        asyncio.run(generate_toc())
    assert not os.path.exists(_toc_path())


def test_generate_toc_model_failure_propagates_and_writes_nothing(tmp_corpus):
    (tmp_corpus / "a.md").write_text("# a", encoding="utf-8")

    class _Boom:
        model = "boom"

        async def generate_content_async(self, request, stream=False):
            raise RuntimeError("provider down")
            yield  # pragma: no cover

    with pytest.raises(RuntimeError, match="provider down"):
        asyncio.run(generate_toc(model=_Boom()))
    assert not os.path.exists(_toc_path())


def test_generate_toc_unwritable_output_dir_raises(tmp_corpus, monkeypatch, tmp_path):
    (tmp_corpus / "a.md").write_text("# a", encoding="utf-8")
    monkeypatch.setattr(config_loader, "get_output_dir", lambda: str(tmp_path / "no" / "such" / "dir"))
    with pytest.raises(OSError):
        asyncio.run(generate_toc())
