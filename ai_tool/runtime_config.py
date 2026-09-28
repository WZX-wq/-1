from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI as _OpenAI


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
CONFIG_FILENAME = "video_ai_config.json"


def _config_candidates() -> tuple[Path, ...]:
    candidates = [Path.cwd() / CONFIG_FILENAME]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent / CONFIG_FILENAME)
    return tuple(dict.fromkeys(candidates))


def _load_file_config() -> dict[str, Any]:
    configured_path = os.getenv("VIDEO_AI_CONFIG", "").strip()
    candidates = (Path(configured_path),) if configured_path else _config_candidates()
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def get_ai_config() -> dict[str, str]:
    file_config = _load_file_config()
    api_key = os.getenv("VIDEO_AI_API_KEY", "").strip() or str(file_config.get("api_key", "")).strip()
    base_url = os.getenv("VIDEO_AI_BASE_URL", "").strip() or str(
        file_config.get("base_url", DEFAULT_BASE_URL)
    ).strip()
    model = os.getenv("VIDEO_AI_MODEL", "").strip() or str(
        file_config.get("model", DEFAULT_MODEL)
    ).strip()
    if not api_key:
        raise RuntimeError(
            "未配置 AI 接口密钥：请设置 VIDEO_AI_API_KEY，或在程序目录创建 video_ai_config.json。"
        )
    if not base_url or not model:
        raise RuntimeError("AI 接口地址和模型名称不能为空。")
    return {"api_key": api_key, "base_url": base_url.rstrip("/"), "model": model}


def create_ai_client(client_factory: Callable[..., object] = _OpenAI) -> object:
    config = get_ai_config()
    return client_factory(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=90,
    )


__all__ = ["CONFIG_FILENAME", "DEFAULT_BASE_URL", "DEFAULT_MODEL", "create_ai_client", "get_ai_config"]
