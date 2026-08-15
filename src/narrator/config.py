"""Tiny config loader — reads config.yaml from the project root."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]


def load(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path else _ROOT / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def project_root() -> Path:
    return _ROOT
