from __future__ import annotations

import json
import importlib
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from urllib.parse import urlsplit

from openai import APIError, OpenAI as _OpenAI


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
CONFIG_FILENAME = "video_ai_config.json"


class AIServiceError(RuntimeError):
    """An actionable API error safe to display without exposing credentials."""


def config_path() -> Path:
    configured_path = os.getenv("VIDEO_AI_CONFIG", "").strip()
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / CONFIG_FILENAME
    if (Path.cwd() / CONFIG_FILENAME).is_file():
        return Path.cwd() / CONFIG_FILENAME
    return Path(__file__).resolve().parent.parent / CONFIG_FILENAME


def _config_candidates() -> tuple[Path, ...]:
    candidates = [Path.cwd() / CONFIG_FILENAME]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent / CONFIG_FILENAME)
    candidates.append(config_path())
    return tuple(dict.fromkeys(candidates))


def _load_file_config() -> dict[str, Any]:
    configured_path = os.getenv("VIDEO_AI_CONFIG", "").strip()
    candidates = (Path(configured_path),) if configured_path else _config_candidates()
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"AI 配置文件无法读取，请在 AI 设置中重新保存：{path}") from error
        if isinstance(data, dict):
            return data
        raise RuntimeError(f"AI 配置文件格式错误，应为 JSON 对象：{path}")
    return {}


def _load_embedded_config() -> dict[str, Any]:
    """Private builds carry defaults in PYZ, never in the public source tree."""
    if not getattr(sys, "frozen", False):
        return {}
    try:
        settings = importlib.import_module("video_ai_embedded_config").SETTINGS
    except ModuleNotFoundError as error:
        if error.name != "video_ai_embedded_config":
            raise
        return {}
    return dict(settings) if isinstance(settings, dict) else {}


def get_ai_config(*, require_key: bool = True) -> dict[str, Any]:
    file_config = _load_file_config()
    embedded = _load_embedded_config()
    base_url = os.getenv("VIDEO_AI_BASE_URL", "").strip() or str(
        file_config.get("base_url", embedded.get("base_url", DEFAULT_BASE_URL))
    ).strip()
    # Never forward the embedded provider's key to a user-entered new host.
    same_provider = base_url.rstrip("/") == str(embedded.get("base_url", "")).rstrip("/")
    defaults = embedded if same_provider else {}
    api_key = (os.getenv("VIDEO_AI_API_KEY", "").strip()
               or str(file_config.get("api_key", "")).strip()
               or str(defaults.get("api_key", "")).strip())
    model = os.getenv("VIDEO_AI_MODEL", "").strip() or str(
        file_config.get("model", defaults.get("model", DEFAULT_MODEL))
    ).strip()
    if require_key and (not api_key or api_key.startswith(("在此填写", "你的", "请填写"))):
        raise RuntimeError(
            "未配置 AI 接口密钥：请在软件 AI 设置中填写并保存，或设置 VIDEO_AI_API_KEY。"
        )
    if not base_url or not model:
        raise RuntimeError("AI 接口地址和模型名称不能为空。")
    parsed = urlsplit(base_url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("AI 接口地址须为有效的 http/https 地址，不能在地址中包含密钥。")
    return {"api_key": api_key, "base_url": base_url.rstrip("/"), "model": model,
            "auto_update_model": file_config.get("auto_update_model", defaults.get("auto_update_model", True)) is True}


def _save_json(data: dict, destination: Path) -> Path:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".video_ai_", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def save_ai_model_state(state: dict, path: Path) -> Path:
    return _save_json(state, path)


def save_ai_config(settings: dict[str, Any], *, path: Path | None = None) -> Path:
    """Save an optional local override without changing embedded defaults."""
    config = {name: str(settings.get(name) or "").strip() for name in ("api_key", "base_url", "model")}
    if not all(config.values()) or config["api_key"].startswith(("在此填写", "你的", "请填写")):
        raise RuntimeError("请填写有效的 AI 接口地址、模型名称和 API Key。")
    parsed = urlsplit(config["base_url"])
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("AI 接口地址须为有效的 http/https 地址，不能在地址中包含密钥。")
    config["base_url"] = config["base_url"].rstrip("/")
    config["auto_update_model"] = settings.get("auto_update_model", True) is True
    destination = Path(path) if path is not None else config_path()
    return _save_json(config, destination)


def ai_error_message(error: object) -> str | None:
    """Distinguish closed models, balance, authentication and transient errors."""
    text = str(error).casefold()
    status = getattr(error, "status_code", None)
    if status == 402 or any(marker in text for marker in (
        "insufficient_quota", "insufficient balance", "insufficientbalance", "quotaexceeded",
        "余额不足", "额度不足", "arrearage", "欠费",
    )):
        return "AI 账号余额或额度不足，请到当前服务商控制台充值或切换自己的可用账号；更换同一账号下的模型不会增加余额。"
    if status == 401 or any(marker in text for marker in ("invalid_api_key", "invalid api key", "authenticationerror")):
        return "AI 接口密钥无效或已失效，请在 AI 设置中填写与接口地址对应的 API Key 并保存。"
    if any(marker in text for marker in ("closedendpoint", "endpoint is closed", "model_not_found", "invalidmodel", "modelnotopen", "endpointnotfound")) or status == 404:
        return "AI 模型端点已关闭、未开通或模型名称不存在，请在 AI 设置中更换当前账号可用的模型并保存。"
    if status == 403:
        return "AI 账号无权调用当前模型，请在服务商控制台开通该模型或在 AI 设置中更换模型。"
    return None


class _ConfiguredCompletions:
    def __init__(self, client: object, config: dict[str, Any]):
        self._client = client
        self._completions = client.chat.completions
        self._config = config

    def create(self, **kwargs):
        # Historical workers still pass old provider model names. The saved
        # configuration is authoritative for every script/topic/tag request.
        kwargs["model"] = self._config["model"]
        host = (urlsplit(self._config["base_url"]).hostname or "").lower()
        if host == "api.deepseek.com" or host.endswith(".volces.com"):
            extra = dict(kwargs.get("extra_body") or {})
            extra.setdefault("thinking", {"type": "disabled"})
            kwargs["extra_body"] = extra
        try:
            from ai_tool.model_updates import ModelAutoUpdater
            return ModelAutoUpdater(self._client, self._config).create(**kwargs)
        except APIError as error:
            message = ai_error_message(error)
            if message:
                raise AIServiceError(message) from error
            # Keep transient failure type/status for the existing retry policy,
            # but redact the configured key if a proxy echoes it in an error.
            raise AIServiceError(str(error).replace(self._config["api_key"], "[已隐藏密钥]")) from error

    def __getattr__(self, name):
        return getattr(self._completions, name)


class ConfiguredAIClient:
    def __init__(self, client: object, config: dict[str, Any]):
        self._client = client
        self.chat = SimpleNamespace(completions=_ConfiguredCompletions(client, config))

    def __getattr__(self, name):
        return getattr(self._client, name)


def create_ai_client(client_factory: Callable[..., object] = _OpenAI) -> object:
    config = get_ai_config()
    client = client_factory(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=90,
        max_retries=2,
    )
    return ConfiguredAIClient(client, config)


__all__ = ["AIServiceError", "CONFIG_FILENAME", "DEFAULT_BASE_URL", "DEFAULT_MODEL", "ai_error_message", "config_path", "create_ai_client", "get_ai_config", "save_ai_config"]
