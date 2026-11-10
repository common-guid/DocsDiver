import os
import logging
from pathlib import Path

from sdaa.src.core.config_loader import config_loader

logger = logging.getLogger(__name__)


def _get_docs_root():
    return os.path.abspath(config_loader.get("system.docs_root", "./docs"))


def resolve_corpus_path(path: str) -> Path:
    """Absolute path of `path` inside the docs root.

    ValueError if the path escapes the root or is reached via a symlink anywhere below the root.
    The caller must open the *returned* resolved path; the lexical input may contain .. that
    collapses safely after normpath because we never open the raw input.
    """
    root = Path(_get_docs_root()).resolve()
    candidate = Path(os.path.normpath(root / path))
    resolved = candidate.resolve()
    if resolved != candidate or not resolved.is_relative_to(root):
        raise ValueError(
            f"Access denied: {path} is outside the documentation root or uses a symlink."
        )
    return resolved


def list_markdown(directory_path: str = ".") -> list[str]:
    """Return a sorted list of corpus-relative .md paths under directory_path.

    - Authorizes the directory via resolve_corpus_path (rejects escapes and symlinks).
    - Skips symlinked files and directories (with one warning each).
    - Does not descend into symlinked directories.
    - Raises FileNotFoundError if the target is not a directory.
    """
    root = Path(_get_docs_root()).resolve()
    target = resolve_corpus_path(directory_path)
    if not target.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    entries: list[str] = []
    for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
        dpath = Path(dirpath)
        # Remove symlinked directories so os.walk does not descend; warn once each
        for d in list(dirnames):
            if (dpath / d).is_symlink():
                rel = (dpath / d).relative_to(root)
                logger.warning(f"Skipping symlinked directory: {rel}")
                dirnames.remove(d)
        for fname in filenames:
            fpath = dpath / fname
            if fpath.is_symlink():
                rel = fpath.relative_to(root)
                logger.warning(f"Skipping symlinked file: {rel}")
                continue
            if fpath.suffix.lower() == ".md":
                rel = fpath.relative_to(root)
                entries.append(str(rel).replace(os.sep, "/"))
    entries.sort()
    return entries


def read_file(file_path: str) -> str:
    """Read the content of a file within the docs root or the generated ToC.

    Args:
        file_path: Path to the file, usually relative to the docs root.

    Returns:
        The content of the file, or an error string if it cannot be read.
    """
    toc_filename = config_loader.get("system.toc_filename", "ToC.json")

    # D4: only the bare configured ToC name is redirected to output_dir.
    # Any other path (including sub/ToC.json or ../x/ToC.json) goes through normal authorization.
    if file_path == toc_filename:
        output_dir = config_loader.get_output_dir()
        full = Path(output_dir) / toc_filename
        if not full.exists():
            return f"Error: File not found: {file_path}"
        try:
            return full.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    try:
        resolved = resolve_corpus_path(file_path)
        if not resolved.exists() or not resolved.is_file():
            return f"Error: File not found: {file_path}"
        return resolved.read_text(encoding="utf-8")
    except ValueError as e:
        logger.warning(str(e))
        return f"Error: Access denied: {file_path} is outside the documentation root or uses a symlink."
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(directory_path: str = ".") -> str:
    """
    Lists files in a directory.
    Args:
        directory_path: Path to the directory, relative to the docs root. Defaults to root.
    Returns:
        A list of file paths relative to the docs root.
    """
    try:
        files = list_markdown(directory_path)
        return "\n".join(files)
    except FileNotFoundError:
        return f"Error: Directory not found: {directory_path}"
    except ValueError as e:
        logger.warning(str(e))
        return f"Error: Access denied: {directory_path} is outside the documentation root or uses a symlink."
