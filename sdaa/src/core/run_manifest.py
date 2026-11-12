"""Run provenance and call accounting, independent of application configuration."""
import hashlib
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
LEDGER: list[dict] = []


def record_call(entry: dict) -> None:
    """Append one completed call without interrupting generation."""
    try:
        LEDGER.append(entry)
    except Exception as e:
        logger.warning("Failed to record model call: %s", e)


def prompt_ref(prompt_obj) -> dict:
    return {"name": getattr(prompt_obj, "name", None), "version": getattr(prompt_obj, "version", None)}


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: str) -> tuple[str, int]:
    lines = []
    for dirpath, dirnames, filenames in os.walk(root):          # does not follow symlinks
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            lines.append((rel, _sha256_file(path)))
    lines.sort()                                                # by relative path, code-point order
    data = "".join(f"{digest}  {rel}\n" for rel, digest in lines)
    return hashlib.sha256(data.encode("utf-8", "surrogateescape")).hexdigest(), len(lines)


def git_state(repo_root: str) -> dict:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo_root, stderr=subprocess.DEVNULL, text=True
        )
        return {"commit": commit, "dirty": bool(status.strip())}
    except Exception:
        return {"commit": None, "dirty": None}


def _usage(calls):
    metered = [entry for entry in calls if entry["metered"]]
    return {
        "calls": len(calls),
        "input_tokens": sum(entry["input_tokens"] for entry in metered),
        "output_tokens": sum(entry["output_tokens"] for entry in metered),
        "total_tokens": sum(entry["total_tokens"] for entry in metered),
        "cost_usd": sum((entry["cost_usd"] or 0.0) for entry in metered),
        "unmetered_calls": len(calls) - len(metered),
    }


def _distinct(values):
    # JSON keys give nulls and strings a stable, comparable ordering.
    unique = {json.dumps(value, sort_keys=True): value for value in values}
    return [unique[key] for key in sorted(unique)]


def write_manifest(path: str, *, run_id, started_at, argv, provider, paths,
                   repo_root, corpus, output_files: dict[str, str], generated: set[str],
                   exit_code: int, problems: list[str]) -> None:
    calls = list(LEDGER)
    agents = {}
    for name in sorted({entry["agent"] for entry in calls if entry["agent"] is not None}):
        entries = [entry for entry in calls if entry["agent"] == name]
        usage = _usage(entries)
        usage.pop("total_tokens")
        agents[name] = {
            "models": _distinct(entry["model"] for entry in entries),
            "providers": _distinct(entry["provider"] for entry in entries),
            "prompts": _distinct(entry["prompt"] for entry in entries),
            **usage,
        }
    outputs = {}
    for name, filename in output_files.items():
        exists = os.path.isfile(filename)
        outputs[name] = {
            "status": ("generated" if filename in generated else "reused") if exists else "missing",
            "sha256": _sha256_file(filename) if exists else None,
        }
    manifest = {
        "schema": 1,
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "argv": list(argv),
        "provider": provider,
        "paths": paths,
        "code": git_state(repo_root),
        "corpus": corpus,
        "agents": agents,
        "usage": _usage(calls),
        "outputs": outputs,
        "outcome": {"exit_code": exit_code, "problems": problems},
        "calls": calls,
    }
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as target:
            temporary = target.name
            json.dump(manifest, target, indent=2)
            target.write("\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)
