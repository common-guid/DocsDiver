from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

DEFAULT_MODELS: Dict[str, str] = {
    "librarian_model": "gemini/gemini-2.0-flash",
    "supervisor_model": "gemini/gemini-2.5-pro",
    "negative_constraints_model": "gemini/gemini-2.0-flash",
    "permissions_model": "gemini/gemini-2.0-flash",
    "boundaries_model": "gemini/gemini-2.0-flash",
}

ENV_OVERRIDES: Dict[str, str] = {
    "librarian_model": "LIBRARIAN_MODEL",
    "supervisor_model": "SUPERVISOR_MODEL",
    "negative_constraints_model": "NEGATIVE_CONSTRAINTS_MODEL",
    "permissions_model": "PERMISSIONS_MODEL",
    "boundaries_model": "BOUNDARIES_MODEL",
}

_CONFIG_CACHE: Optional[Dict[str, str]] = None


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config.yaml"


def _load_yaml(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_model_config(force_reload: bool = False) -> Dict[str, str]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not force_reload:
        return dict(_CONFIG_CACHE)

    config = dict(DEFAULT_MODELS)
    yaml_data = _load_yaml(_config_path())

    for key, default in DEFAULT_MODELS.items():
        value = yaml_data.get(key, default)
        if isinstance(value, str) and value.strip():
            config[key] = value.strip()

    for key, env_var in ENV_OVERRIDES.items():
        env_value = os.getenv(env_var)
        if env_value and env_value.strip():
            config[key] = env_value.strip()

    _CONFIG_CACHE = dict(config)
    return config


def get_librarian_model() -> str:
    return load_model_config().get("librarian_model", DEFAULT_MODELS["librarian_model"])


def get_supervisor_model() -> str:
    return load_model_config().get("supervisor_model", DEFAULT_MODELS["supervisor_model"])


def get_negative_constraints_model() -> str:
    return load_model_config().get(
        "negative_constraints_model",
        DEFAULT_MODELS["negative_constraints_model"],
    )


def get_permissions_model() -> str:
    return load_model_config().get(
        "permissions_model",
        DEFAULT_MODELS["permissions_model"],
    )


def get_boundaries_model() -> str:
    return load_model_config().get(
        "boundaries_model",
        DEFAULT_MODELS["boundaries_model"],
    )
