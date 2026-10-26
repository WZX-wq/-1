"""Portable local preferences for speech providers."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def normalize_tts_provider(value, default: int = 1) -> int:
    """Return one of the supported providers: Edge (0) or Baidu (1)."""
    try:
        provider = int(value)
    except (TypeError, ValueError):
        provider = default
    return provider if provider in (0, 1) else default


def _read_json(path: Path, default: dict) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return dict(default)
    return value if isinstance(value, dict) else dict(default)


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)
    return path


def load_voice_preferences() -> dict:
    preferences = _read_json(
        app_directory() / "voice_preferences.json",
        {"api_type": None, "random_voice": True, "edge_voice_options": []},
    )
    if preferences.get("api_type") is not None:
        preferences["api_type"] = normalize_tts_provider(preferences["api_type"])
    return preferences


def save_voice_preferences(
    api_type: int,
    random_voice: bool,
    edge_voice_options: list[str] | None = None,
) -> Path:
    current = load_voice_preferences()
    return _write_json(
        app_directory() / "voice_preferences.json",
        {
            "api_type": normalize_tts_provider(api_type),
            "random_voice": bool(random_voice),
            "edge_voice_options": list(edge_voice_options or current.get("edge_voice_options", [])),
        },
    )
