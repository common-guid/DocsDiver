from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

DEFAULT_PATHS: Dict[str, str] = {
    "docs_dir": "./docs",
    "toc_path": "./ToC.json",
    "artifacts": "./artifacts",
}

ENV_OVERRIDES: Dict[str, str] = {
    "docs_dir": "DOCS_DIR",
    "toc_path": "TOC_PATH",
    "artifacts": "ARTIFACTS_DIR",
}

_CONFIG_CACHE: Optional[Dict[str, str]] = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _config_path() -> Path:
    return _project_root() / "config.yaml"


def _load_yaml(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = _project_root() / path
    return path


def load_app_config(force_reload: bool = False) -> Dict[str, str]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not force_reload:
        return dict(_CONFIG_CACHE)

    config = dict(DEFAULT_PATHS)
    yaml_data = _load_yaml(_config_path())

    for key, default in DEFAULT_PATHS.items():
        value = yaml_data.get(key, default)
        if isinstance(value, str) and value.strip():
            config[key] = value.strip()

    for key, env_var in ENV_OVERRIDES.items():
        env_value = os.getenv(env_var)
        if env_value and env_value.strip():
            config[key] = env_value.strip()

    _CONFIG_CACHE = dict(config)
    return config


def get_docs_dir(cli_override: str | None = None) -> Path:
    if cli_override and cli_override.strip():
        return _resolve_path(cli_override)
    return _resolve_path(load_app_config().get("docs_dir", DEFAULT_PATHS["docs_dir"]))


def get_toc_path() -> Path:
    return _resolve_path(load_app_config().get("toc_path", DEFAULT_PATHS["toc_path"]))


def get_artifacts_dir() -> Path:
    return _resolve_path(load_app_config().get("artifacts", DEFAULT_PATHS["artifacts"]))
