"""Load shared configuration without contacting Ollama or loading data."""

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_settings(path: str | Path = "config/settings.yaml") -> dict[str, Any]:
    """Resolve relative paths against the project root and read YAML."""
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    try:
        with config_path.open("r", encoding="utf-8-sig") as handle:
            settings = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(settings, dict):
        raise ValueError("The settings file must contain a YAML mapping.")

    required_sections = (
        "project", "llm", "retrieval", "dataset", "rair", "kair", "paths"
    )
    for section in required_sections:
        if not isinstance(settings.get(section), dict):
            raise ValueError(f"Missing or invalid settings section: {section}")

    return settings
