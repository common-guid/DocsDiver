"""Safe corpus inspection and reproducible exact-edit builds."""

import os
from pathlib import Path
import re

from sdaa.src.core.run_manifest import tree_hash


class CorpusError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


def verify(root) -> list[str]:
    root = Path(root)
    if not root.is_dir():
        return ["root missing or not a directory"]
    if root.is_symlink():
        return ["symlink: ."]
    problems = []
    contents = {}
    markdown = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                problems.append(f"symlink: {relative}")
                if name in dirs:
                    dirs.remove(name)
                continue
            if name in dirs:
                continue
            if not name.endswith(".md"):
                problems.append(f"non-Markdown file: {relative}")
            else:
                markdown += 1
            try:
                contents.setdefault(path.read_bytes(), []).append(relative)
            except OSError as exc:
                problems.append(f"cannot read {relative}: {exc}")
    for paths in contents.values():
        if len(paths) > 1:
            problems.append("duplicate bytes: " + ", ".join(sorted(paths)))
    if not markdown:
        problems.append("no .md files")
    return sorted(problems)


# ponytail: ATX headings and simple fence toggling only; no setext headings or fence-length matching
def _heading_offsets(text):
    fenced = False
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.strip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced:
            match = re.match(r"^ {0,3}#{1,6}\s+(.*?)(?:\s+#+)?\s*$", line)
            if match:
                yield offset, match.group(1)
        offset += len(line)


def headings(text) -> list[str]:
    return [heading for _, heading in _heading_offsets(text)]


def section_at(text, offset) -> str:
    section = ""
    for start, heading in _heading_offsets(text):
        if start >= offset:
            break
        section = heading
    return section


def build(clean, seeded, edits) -> dict:
    clean, seeded = Path(clean), Path(seeded)
    verification = verify(clean)
    problems = list(verification)
    source, target = clean.resolve(), seeded.resolve()
    if seeded.exists() or seeded.is_symlink():
        problems.append("seeded path already exists")
    if source == target or source in target.parents or target in source.parents:
        problems.append("clean and seeded paths must not contain one another")
    originals = {}
    texts = {}
    # Do not traverse a corpus that verification found unsafe.
    if not verification:
        for path in sorted(clean.rglob("*")):
            if path.is_file():
                relative = path.relative_to(clean).as_posix()
                try:
                    originals[relative] = path.read_bytes()
                    texts[relative] = originals[relative].decode("utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    problems.append(f"{relative}: cannot decode UTF-8: {exc}")
    spans = {}
    for item_id, path, find, replace in edits:
        if path not in originals:
            problems.append(f"{item_id}: {path}: not a clean file")
            continue
        if path not in texts:
            continue
        count = texts[path].count(find)
        if not find or count != 1:
            detail = "zero occurrences" if count == 0 else "two-or-more occurrences"
            problems.append(f"{item_id}: {path}: find has {detail}")
            continue
        start = texts[path].index(find)
        spans.setdefault(path, []).append((start, start + len(find), replace, item_id))
    for path, changes in spans.items():
        changes.sort()
        for index, current in enumerate(changes):
            for previous in changes[:index]:
                if current[0] < previous[1]:
                    problems.append(f"{current[3]}: {path}: overlapping edit with {previous[3]}")
    if problems:
        raise CorpusError(problems)
    output = dict(originals)
    for path, changes in spans.items():
        text = texts[path]
        for start, end, replace, _ in reversed(changes):
            text = text[:start] + replace + text[end:]
        output[path] = text.encode("utf-8")
    for relative, data in output.items():
        path = seeded / relative
        os.makedirs(path.parent, exist_ok=True)
        path.write_bytes(data)
    actual = sorted(path.relative_to(seeded).as_posix() for path in seeded.rglob("*") if path.is_file())
    if actual != sorted(originals):
        raise CorpusError(["seeded file list differs from clean"])
    result = {}
    for name, root in (("clean", clean), ("seeded", seeded)):
        digest, count = tree_hash(root)
        result[name] = {"tree_hash": digest, "files": count}
    return result
