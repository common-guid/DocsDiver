"""Validity checks for the ToC and audit outputs, and the move-aside helper.

Reuse and success decisions in main.py rest on these checks instead of file existence.
Each check returns a list of human-readable problems; an empty list means valid.
Not checked here: whether the ToC covers the *current* corpus (freshness detection).
"""
import json
import os
from pathlib import Path
from typing import List

from sdaa.src.core.config_loader import config_loader
from sdaa.src.tools import file_ops

SKIPPED_PREFIX = "SKIPPED:"  # legacy placeholder written by older --coordinator-only runs
ERROR_SUMMARY_PREFIX = "Error reading file:"  # legacy swallowed Map Maker read error
REPORT_FILENAME = "Security_Threat_Model.md"
# session-state key -> artifact filename (reporting.py keeps its own literals)
WORKER_ARTIFACTS = {
    "permissions_report": "permissions_agent.md",
    "constraints_report": "constraints_agent.md",
    "boundaries_report": "boundaries_agent.md",
}


def audit_output_paths() -> List[str]:
    """The three worker artifacts followed by the final report."""
    artifacts_dir = config_loader.get_artifacts_dir()
    reports_dir = config_loader.get_reports_dir()
    return [os.path.join(artifacts_dir, n) for n in WORKER_ARTIFACTS.values()] + [
        os.path.join(reports_dir, REPORT_FILENAME)
    ]


def toc_problems(toc_path: str) -> List[str]:
    try:
        with open(toc_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [f"ToC not found: {toc_path}"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return [f"ToC is not readable JSON ({toc_path}): {e}"]

    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, list) or not files:
        return [f"ToC must be an object with a non-empty 'files' list: {toc_path}"]

    problems: List[str] = []
    docs_root = Path(file_ops._get_docs_root()).resolve()
    seen = set()
    for i, entry in enumerate(files):
        where = f"ToC entry {i}"
        if not isinstance(entry, dict):
            problems.append(f"{where} is not an object")
            continue
        path, summary, tags = entry.get("path"), entry.get("summary"), entry.get("tags")
        if not isinstance(path, str) or not path.strip():
            problems.append(f"{where} has no 'path'")
            continue
        where = f"ToC entry '{path}'"
        if path in seen:
            problems.append(f"{where} is duplicated")
        seen.add(path)
        if not isinstance(summary, str) or not summary.strip():
            problems.append(f"{where} has an empty summary")
        elif summary.lstrip().startswith(ERROR_SUMMARY_PREFIX):
            problems.append(f"{where} has an error as its summary")
        if not (isinstance(tags, list) and len(tags) == 3
                and all(isinstance(t, str) and t.strip() for t in tags)):
            problems.append(f"{where} must have exactly 3 non-empty tags")
        target = (docs_root / path).resolve()
        if not target.is_relative_to(docs_root) or not target.is_file():
            problems.append(f"{where} is not a file inside the docs root")
    return problems


def text_output_problems(path: str) -> List[str]:
    """Validity of a worker artifact or the final report."""
    if not os.path.isfile(path):
        return [f"missing: {path}"]
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return [f"unreadable: {path} ({e})"]
    if not content.strip():
        return [f"empty: {path}"]
    if content.lstrip().startswith(SKIPPED_PREFIX):
        return [f"placeholder (SKIPPED): {path}"]
    return []


def audit_output_problems() -> List[str]:
    return [p for path in audit_output_paths() for p in text_output_problems(path)]


def set_aside(paths: List[str]) -> None:
    """Rename each existing path to '<path>.prev', replacing any older '.prev'.

    Used before regenerating an output, so a failed regeneration leaves the output
    missing (not stale) while the previous result survives.
    """
    for p in paths:
        if os.path.exists(p):
            os.replace(p, p + ".prev")
