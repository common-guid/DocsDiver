"""Answer-key schema, byte hashes, and corpus-aware checks."""

import hashlib
from pathlib import Path, PurePosixPath
import re

import yaml

from .corpus import headings, section_at

TAGS_VERSION = 1
AREA_TAGS = {"permission-gap", "invariant-gap", "trust-boundary-gap"}
CROSS_TAGS = {"contradiction"}
KINDS = {"planted": "PL", "native": "NA", "incidental": "IN", "invented": "RJ", "disputed": "DS"}
STATUSES = {"draft", "approved", "retired"}
EFFECTS = {"none", "hidden", "altered"}
LABEL_WORDS = re.compile(r"\b(planted|seeded|intentional(ly)?)\b|\b(PL|NA|IN|RJ|DS)-\d+\b", re.I)


def key_hash(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path) -> dict:
    try:
        result = yaml.safe_load(Path(path).read_bytes())
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid key YAML: {exc}") from exc
    if not isinstance(result, dict):
        raise ValueError("key must be a mapping")
    return result


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _member(value, choices):
    return isinstance(value, str) and value in choices


def _path(value):
    return (isinstance(value, str) and value.endswith(".md")
            and not value.startswith(("/", "\\"))
            and "\\" not in value and ".." not in PurePosixPath(value).parts)


def _strings(mapping, names):
    return (isinstance(mapping, dict) and set(mapping) == set(names)
            and all(isinstance(mapping[name], str) for name in names))


def check(key: dict, clean_dir) -> list[str]:
    header = []
    expected = {"key_id", "key_version", "snapshot_id", "tags_version", "items"}
    if not isinstance(key, dict):
        return ["header: key must be a mapping"]
    for name in sorted(set(key) - expected, key=str):
        header.append(f"header: unknown field {name}")
    for name in ("key_id", "snapshot_id"):
        if not _nonempty(key.get(name)):
            header.append(f"header: {name} must be a non-empty string")
    version = key.get("key_version")
    if type(version) is not int or version < 1:
        header.append("header: key_version must be an integer >= 1")
    if type(key.get("tags_version")) is not int or key["tags_version"] != TAGS_VERSION:
        header.append(f"header: tags_version must be {TAGS_VERSION}")
    if not isinstance(key.get("items"), list):
        return header + ["header: items must be a list"]
    items = key["items"]
    errors = [[] for _ in items]
    seen = set()
    plant_ids = {item["id"] for item in items if isinstance(item, dict)
                 and isinstance(item.get("id"), str) and item.get("kind") == "planted"
                 and item.get("status") != "retired"}
    clean = Path(clean_dir)
    cache = {}

    def read(relative):
        if not _path(relative):
            return None
        if relative not in cache:
            path = clean / relative
            parts = [clean.joinpath(*PurePosixPath(relative).parts[:i])
                     for i in range(1, len(PurePosixPath(relative).parts) + 1)]
            try:
                if clean.is_symlink() or any(part.is_symlink() for part in parts):
                    return None
                if not path.resolve().is_relative_to(clean.resolve()):
                    return None
                cache[relative] = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                cache[relative] = None
        return cache[relative]

    page_owners = {}
    edited_sections = []
    base_fields = {"id", "kind", "status", "tags", "variants", "locations",
                   "what", "why", "note", "added_in"}
    for index, item in enumerate(items):
        label = item.get("id", f"item[{index}]") if isinstance(item, dict) else f"item[{index}]"

        def problem(message):
            errors[index].append(f"{label}: {message}")

        if not isinstance(item, dict):
            problem("item must be a mapping")
            continue
        kind = item.get("kind")
        valid_kind = _member(kind, KINDS)
        if not valid_kind:
            problem("unknown kind")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not re.fullmatch(r"(PL|NA|IN|RJ|DS)-\d{2,}", item_id):
            problem("invalid id")
        elif valid_kind and item_id.split("-")[0] != KINDS[kind]:
            problem("id prefix does not match kind")
        if isinstance(item_id, str):
            if item_id in seen:
                problem("duplicate id")
            seen.add(item_id)
        if not _member(item.get("status"), STATUSES):
            problem("unknown status")
        allowed = base_fields | ({"difficulty", "plant", "confounded"} if kind == "planted" else {"source"})
        if kind == "native":
            allowed |= {"interaction"}
        for name in sorted(set(item) - allowed, key=str):
            problem(f"field not allowed: {name}")
        tags = item.get("tags")
        if (not isinstance(tags, list) or not all(_member(tag, AREA_TAGS | CROSS_TAGS) for tag in tags)
                or len(set(tag for tag in tags if isinstance(tag, str))) != len(tags)
                or not 1 <= sum(tag in AREA_TAGS for tag in tags if isinstance(tag, str)) <= 2):
            problem("tags need one or two area tags, no duplicates or unknown tags")
        variants = item.get("variants")
        if (not isinstance(variants, list) or not variants
                or not all(_member(v, {"clean", "seeded"}) for v in variants)
                or len(set(v for v in variants if isinstance(v, str))) != len(variants)):
            problem("invalid variants")
        if kind in ("planted", "incidental") and variants != ["seeded"]:
            problem("variants must be [seeded]")
        for name in ("what", "why"):
            required = name == "what" or kind in ("planted", "native", "incidental")
            if (required or name in item) and not _nonempty(item.get(name)):
                problem(f"{name} must be a non-empty string")
        if "note" in item and not isinstance(item["note"], str):
            problem("note must be a string")
        added = item.get("added_in")
        if type(added) is not int or added < 1 or (type(version) is int and added > version):
            problem("added_in must be an integer from 1 to key_version")
        locations = item.get("locations")
        valid_locations = []
        if not isinstance(locations, list) or not 1 <= len(locations) <= 2:
            problem("locations must contain one or two mappings")
        else:
            for location in locations:
                if not _strings(location, ("path", "section")) or not _path(location["path"]):
                    problem("invalid location path or section")
                else:
                    valid_locations.append(location)
        if "source" in item and not _strings(item["source"], ("run", "finding")):
            problem("source must contain run and finding strings")
        interaction = item.get("interaction")
        if "interaction" in item:
            if (not _strings(interaction, ("plant", "effect"))
                    or interaction["plant"] not in plant_ids or interaction["effect"] not in EFFECTS):
                problem("interaction must name a non-retired plant and a valid effect")
            if (kind == "native" and isinstance(interaction, dict)
                    and interaction.get("effect") in ("hidden", "altered") and variants != ["clean"]):
                problem("hidden or altered native variants must be [clean]")
        edits = []
        if kind == "planted":
            difficulty = item.get("difficulty")
            if type(difficulty) is not int or not 1 <= difficulty <= 3:
                problem("difficulty must be an integer 1–3")
            if "confounded" in item and type(item["confounded"]) is not bool:
                problem("confounded must be a bool")
            plant = item.get("plant")
            if not isinstance(plant, list) or not plant:
                problem("plant must be a non-empty list")
            else:
                for edit in plant:
                    if not _strings(edit, ("path", "find", "replace")) or not _path(edit["path"]) or not edit["find"]:
                        problem("invalid plant edit")
                    else:
                        edits.append(edit)
        if item.get("status") == "retired":
            continue
        for location in valid_locations:
            text = read(location["path"])
            if text is None:
                problem(f"{location['path']}: location file missing or unreadable")
            elif location["section"] and location["section"] not in headings(text):
                problem(f"{location['path']}: unknown section {location['section']}")
        for edit in edits:
            path = edit["path"]
            if path not in [location["path"] for location in valid_locations]:
                problem(f"{path}: plant path is not a location")
            if path in page_owners and page_owners[path] != index:
                problem(f"{path}: more than one planted item edits this page")
            page_owners[path] = index
            if LABEL_WORDS.search(edit["replace"]):
                problem(f"{path}: replace contains an answer-key label")
            text = read(path)
            if text is None or text.count(edit["find"]) != 1:
                problem(f"{path}: find must occur exactly once in clean text")
            else:
                edited_sections.append((path, section_at(text, text.index(edit["find"])), item_id))
    # Rule 2: interactions are section-based, not page-based.
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("kind") != "native" or item.get("status") == "retired":
            continue
        locations = item.get("locations")
        if not isinstance(locations, list):
            continue
        for path, section, plant_id in edited_sections:
            if any(location == {"path": path, "section": section} for location in locations):
                interaction = item.get("interaction")
                if not isinstance(interaction, dict) or interaction.get("plant") != plant_id:
                    errors[index].append(f"{item.get('id', f'item[{index}]')}: interaction.plant must be {plant_id}")
    return header + [problem for group in errors for problem in group]


def approved_edits(key) -> list[tuple]:
    return [(item["id"], edit["path"], edit["find"], edit["replace"])
            for item in key["items"] if item["kind"] == "planted" and item["status"] == "approved"
            for edit in item["plant"]]
