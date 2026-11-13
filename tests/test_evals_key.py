import ast
import copy
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from evals import key

EXAMPLE = Path(__file__).resolve().parents[1] / "evals" / "examples" / "acme"
ROOT = EXAMPLE.parents[2]


def _key():
    return copy.deepcopy(key.load(EXAMPLE / "key.yaml"))


def _cli(*args):
    return subprocess.run([sys.executable, "-m", "evals", *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True)


def test_example_key():
    assert key.check(_key(), EXAMPLE / "clean") == []
    result = _cli("key", "check", "--key", EXAMPLE / "key.yaml", "--clean", EXAMPLE / "clean")
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == f"OK acme-example v2 sha256 {key.key_hash(EXAMPLE / 'key.yaml')}, 6 items\n"


@pytest.mark.parametrize("suffix", [b"\n# comment A\n", b"\n "])
def test_hash_raw_bytes(tmp_path, suffix):
    path = tmp_path / "key.yaml"
    original = (EXAMPLE / "key.yaml").read_bytes()
    path.write_bytes(original)
    first = key.key_hash(path)
    assert first == hashlib.sha256(original).hexdigest()
    path.write_bytes(original + suffix)
    assert key.key_hash(path) != first
    assert key.key_hash(path) == hashlib.sha256(path.read_bytes()).hexdigest()
    assert key.load(path)["key_version"] == 2
    if b"comment" in suffix:
        first = key.key_hash(path)
        path.write_bytes(path.read_bytes().replace(b"comment A", b"comment B"))
        assert key.key_hash(path) != first


# A path into the example mapping and a replacement (None deletes the field).
@pytest.mark.parametrize("path,value,label", [
    (("items", 0, "tags"), ["unknown"], "PL-01"),
    (("items", 0, "tags"), [], "PL-01"),
    (("items", 0, "tags"), ["contradiction"], "PL-01"),
    (("items", 0, "tags"), sorted(key.AREA_TAGS), "PL-01"),
    (("items", 1, "id"), "PL-01", "PL-01"),
    (("items", 0, "id"), "NA-01", "NA-01"),
    (("items", 0, "plant"), None, "PL-01"),
    (("items", 0, "difficulty"), None, "PL-01"),
    (("items", 0, "difficulty"), 4, "PL-01"),
    (("items", 0, "difficulty"), True, "PL-01"),
    (("items", 0, "variants"), ["clean", "seeded"], "PL-01"),
    (("items", 0, "interaction"), {"plant": "PL-02", "effect": "none"}, "PL-01"),
    (("items", 0, "source"), {"run": "r", "finding": "f"}, "PL-01"),
    (("items", 2, "why"), None, "NA-02"),
    (("items", 0, "unknown"), 1, "PL-01"),
    (("items", 0, "added_in"), 3, "PL-01"),
    (("tags_version",), 2, "header"),
    (("unknown",), 1, "header"),
    (("items", 0, "locations", 0, "path"), "../roles.md", "PL-01"),
    (("items", 0, "locations", 0, "path"), "roles.txt", "PL-01"),
    (("items", 0, "locations", 0, "section"), "Missing", "PL-01"),
    (("items", 0, "locations", 0, "path"), "absent.md", "PL-01"),
    (("items", 0, "plant", 0, "path"), "api/tokens.md", "PL-01"),
    (("items", 0, "plant", 0, "find"), "absent sentence", "PL-01"),
    (("items", 1, "plant", 0, "path"), "sharing/links.md", "PL-02"),
    (("items", 0, "plant", 0, "replace"), "The seeded text.", "PL-01"),
    (("items", 0, "plant", 0, "replace"), "See NA-03.", "PL-01"),
    (("items", 2, "interaction", "plant"), "PL-99", "NA-02"),
    (("items", 2, "interaction", "effect"), "hidden", "NA-02"),
    (("key_version",), True, "header"),
    (("tags_version",), True, "header"),
    (("key_id",), "", "header"),
    (("snapshot_id",), "", "header"),
    (("items",), {}, "header"),
    (("items", 0, "kind"), "other", "PL-01"),
    (("items", 0, "status"), "other", "PL-01"),
    (("items", 0, "id"), "PL-1", "PL-1"),
    (("items", 0, "tags"), ["permission-gap", "permission-gap"], "PL-01"),
    (("items", 0, "tags"), [{}], "PL-01"),
    (("items", 0, "variants"), [], "PL-01"),
    (("items", 0, "variants"), ["seeded", "seeded"], "PL-01"),
    (("items", 0, "variants"), ["other"], "PL-01"),
    (("items", 0, "locations"), [], "PL-01"),
    (("items", 0, "locations", 0, "extra"), "x", "PL-01"),
    (("items", 0, "locations", 0, "path"), "/roles.md", "PL-01"),
    (("items", 0, "locations", 0, "path"), "admin\\roles.md", "PL-01"),
    (("items", 0, "what"), " ", "PL-01"),
    (("items", 0, "note"), 1, "PL-01"),
    (("items", 0, "added_in"), True, "PL-01"),
    (("items", 0, "confounded"), "yes", "PL-01"),
    (("items", 0, "plant"), [], "PL-01"),
    (("items", 0, "plant", 0, "find"), "", "PL-01"),
    (("items", 0, "plant", 0, "extra"), "x", "PL-01"),
    (("items", 2, "difficulty"), 1, "NA-02"),
    (("items", 2, "interaction", "effect"), "other", "NA-02"),
    (("items", 2, "source", "run"), 2, "NA-02"),
], ids=lambda value: str(value))
def test_key_rejects_mutation(path, value, label):
    data = _key()
    parent = data
    for part in path[:-1]:
        parent = parent[part]
    if value is None:
        del parent[path[-1]]
    else:
        parent[path[-1]] = value
    problems = key.check(data, EXAMPLE / "clean")
    assert any(problem.startswith(label + ":") for problem in problems), problems


def test_rule_two_section_not_page():
    data = _key()
    del data["items"][2]["interaction"]
    assert key.check(data, EXAMPLE / "clean") == ["NA-02: interaction.plant must be PL-01"]
    data["items"][2]["locations"][0]["section"] = "Creating links"
    assert key.check(data, EXAMPLE / "clean") == []


def test_retired_skips_corpus_checks():
    data = _key()
    plant = data["items"][1]
    plant["status"] = "retired"
    plant["plant"][0]["find"] = "not present"
    plant["plant"][0]["replace"] = "seeded"
    plant["locations"][0]["path"] = "absent.md"
    assert key.check(data, EXAMPLE / "clean") == []
    plant["difficulty"] = True
    assert any(p.startswith("PL-02: difficulty") for p in key.check(data, EXAMPLE / "clean"))


def test_approved_edits():
    data = _key()
    edit = data["items"][0]["plant"][0]
    assert key.approved_edits(data) == [("PL-01", edit["path"], edit["find"], edit["replace"])]


@pytest.mark.parametrize("invalid", [False, True])
def test_cli_build_rejects_key(tmp_path, invalid):
    data = _key()
    if invalid:
        data["items"][0]["difficulty"] = 4
    else:
        data["items"][0]["status"] = "draft"
    path = tmp_path / "key.yaml"
    path.write_text(yaml.safe_dump(data))
    seeded = tmp_path / "seeded"
    result = _cli("corpus", "build", "--key", path, "--clean", EXAMPLE / "clean",
                  "--seeded", seeded, "--variants", tmp_path / "variants.yaml")
    assert result.returncode == 1
    assert ("PL-01" if invalid else "no approved plants") in result.stderr
    assert not result.stdout
    assert not seeded.exists()
    assert not (tmp_path / "variants.yaml").exists()


@pytest.mark.parametrize("text", ["[]", "null", "a string"])
def test_load_requires_mapping(tmp_path, text):
    path = tmp_path / "key.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match="mapping"):
        key.load(path)


def test_cli_usage_and_verify_failure(tmp_path):
    result = _cli("key", "check")
    assert result.returncode == 2
    result = _cli("corpus", "verify", tmp_path / "missing")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "root missing or not a directory\n"


def test_cli_build_corpus_error(tmp_path):
    seeded = tmp_path / "exists"
    seeded.mkdir()
    result = _cli("corpus", "build", "--key", EXAMPLE / "key.yaml",
                  "--clean", EXAMPLE / "clean", "--seeded", seeded,
                  "--variants", tmp_path / "variants.yaml")
    assert result.returncode == 1
    assert "seeded path already exists" in result.stderr
    assert not (tmp_path / "variants.yaml").exists()


def test_import_boundaries():
    script = ("import sys; import evals.__main__; "
              "assert 'evals.key' not in sys.modules; "
              "import evals.corpus; assert 'evals.key' not in sys.modules")
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    tree = ast.parse((ROOT / "evals/corpus.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "key"


def test_hidden_native_and_empty_replace_allowed():
    data = _key()
    data["items"][2]["interaction"]["effect"] = "hidden"
    data["items"][2]["variants"] = ["clean"]
    data["items"][0]["plant"][0]["replace"] = ""
    assert key.check(data, EXAMPLE / "clean") == []


def test_interaction_cannot_reference_retired_plant():
    data = _key()
    data["items"][0]["status"] = "retired"
    assert any(p.startswith("NA-02: interaction") for p in key.check(data, EXAMPLE / "clean"))


def test_problems_in_item_order():
    data = _key()
    data["items"][0]["difficulty"] = False
    data["items"][2]["what"] = ""
    del data["items"][2]["interaction"]
    problems = key.check(data, EXAMPLE / "clean")
    assert [p.split(":")[0] for p in problems] == ["PL-01", "NA-02", "NA-02"]


def test_only_one_plant_per_page():
    data = _key()
    second = copy.deepcopy(data["items"][0])
    second["id"] = "PL-03"
    second["plant"][0]["find"] = "A public link lets anyone with the URL"
    data["items"].append(second)
    problems = key.check(data, EXAMPLE / "clean")
    assert problems == ["PL-03: sharing/links.md: more than one planted item edits this page"]


def test_cli_malformed_yaml(tmp_path):
    path = tmp_path / "key.yaml"
    path.write_text("items: [")
    with pytest.raises(ValueError, match="invalid key YAML"):
        key.load(path)
    result = _cli("key", "check", "--key", path, "--clean", EXAMPLE / "clean")
    assert result.returncode == 1
    assert "invalid key YAML" in result.stderr
    assert "Traceback" not in result.stderr


def test_schema_bad_shapes_do_not_crash():
    for field in ("kind", "status", "tags", "variants", "locations", "plant", "interaction"):
        data = _key()
        data["items"][0][field] = {}
        assert key.check(data, EXAMPLE / "clean")
    assert key.check([], EXAMPLE / "clean") == ["header: key must be a mapping"]


def test_incidental_seeded_only():
    data = _key()
    item = data["items"][4]
    item["id"], item["kind"] = "IN-01", "incidental"
    assert any(p.startswith("IN-01: variants") for p in key.check(data, EXAMPLE / "clean"))
    item["variants"] = ["seeded"]
    assert key.check(data, EXAMPLE / "clean") == []
