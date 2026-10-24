"""Same-provider model discovery with bounded retries and last-working fallback."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from openai import APIError


_LOCK = threading.RLock()
_CACHE: dict[str, dict] = {}
CHECK_INTERVAL_SECONDS = 24 * 60 * 60


def _model_version(model: str):
    match = re.fullmatch(r'doubao-seed-(\d+)-(\d+)-(lite|mini|pro|turbo)-(\d{6})', model)
    if match:
        return match[3], (int(match[1]), int(match[2]), int(match[4]))
    return None


def compatible_models(models, current_model: str, *, newer_only: bool) -> list[str]:
    """Never switch providers, price tiers, previews or output modalities."""
    current = _model_version(current_model)
    if current is None:
        return []
    candidates = []
    for item in models:
        data = item if isinstance(item, dict) else item.model_dump()
        identifier = str(data.get('id', ''))
        version = _model_version(identifier)
        if not version or identifier == current_model or version[0] != current[0]:
            continue
        if newer_only and version[1] <= current[1]:
            continue
        if str(data.get('status') or '').casefold() not in ('', 'active', 'running', 'available', 'online', 'ready'):
            continue
        modalities = data.get('modalities') or {}
        if 'text' not in modalities.get('output_modalities', []):
            continue
        if 'TextGeneration' not in data.get('task_type', []):
            continue
        candidates.append((version[1], identifier))
    return [identifier for _version, identifier in sorted(candidates, reverse=True)][:2]


def _is_closed_model(error: APIError) -> bool:
    status = getattr(error, 'status_code', None)
    text = str(error).casefold()
    return status == 404 or any(marker in text for marker in (
        'closedendpoint', 'endpointnotfound', 'model_not_found', 'modelnotopen', 'invalidmodel',
    ))


class ModelAutoUpdater:
    def __init__(self, client, config: dict):
        self.client = client
        self.config = config

    def _state_identity(self, model: str) -> str:
        from ai_tool.runtime_config import config_path
        material = '\0'.join((str(config_path()), self.config['base_url'], self.config['api_key'], model))
        return hashlib.sha256(material.encode()).hexdigest()

    def _state_path(self) -> Path:
        from ai_tool.runtime_config import config_path
        return config_path().with_name('video_ai_model_state.json')

    def _last_check(self, model: str) -> dict:
        identity = self._state_identity(model)
        if identity in _CACHE:
            return _CACHE[identity]
        try:
            data = json.loads(self._state_path().read_text(encoding='utf-8'))
            state = data.get(identity, {})
            if isinstance(state, dict):
                return state
        except (OSError, ValueError, AttributeError):
            pass
        return {}

    def _remember(self, model: str, *, checked: bool = True) -> None:
        from ai_tool.runtime_config import save_ai_model_state
        state = {'checked_at': time.time() if checked else 0, 'resolved_model': model}
        identities = (self._state_identity(self.config['model']), self._state_identity(model))
        for identity in identities:
            _CACHE[identity] = state
        try:
            path = self._state_path()
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    data = {}
            except (OSError, ValueError):
                data = {}
            for identity in identities:
                data[identity] = state
            # Avoid letting old account/model entries grow without a bound.
            recent = sorted(data.items(), key=lambda pair: pair[1].get('checked_at', 0), reverse=True)[:20]
            save_ai_model_state(dict(recent), path)
        except (OSError, RuntimeError, TypeError, AttributeError):
            pass  # A read-only folder must not invalidate a generated result.

    def _catalog(self, current: str, *, newer_only: bool) -> list[str]:
        try:
            page = self.client.with_options(timeout=10, max_retries=0).models.list()
            return compatible_models(page.data, current, newer_only=newer_only)
        except (APIError, ValueError, TypeError, AttributeError):
            return []  # A catalog outage must not block the last-working model.

    def _persist_working_model(self, model: str) -> None:
        from ai_tool.runtime_config import _load_file_config, _save_json, config_path, get_ai_config
        try:
            settings = _load_file_config()
            # Persist only if the user has not changed settings in the meantime.
            # With embedded credentials the model override stays key-free.
            if get_ai_config() == self.config:
                settings.update(base_url=self.config['base_url'], model=model,
                                auto_update_model=self.config.get('auto_update_model', True))
                _save_json(settings, config_path())
            logging.info('AI 模型自动更新：%s -> %s', self.config['model'], model)
        except (OSError, RuntimeError):
            pass

    def _request(self, model: str, kwargs):
        response = self.client.chat.completions.create(**{**kwargs, 'model': model})
        # A truncated/empty response is not evidence of a usable replacement.
        if not getattr(response, 'choices', None) or not getattr(response.choices[0].message, 'content', None):
            raise RuntimeError('AI 返回空内容，未切换模型，请稍后重试。')
        if getattr(response.choices[0], 'finish_reason', None) == 'length':
            raise RuntimeError('AI 返回内容被截断，未切换模型，请增加输出长度后重试。')
        return response

    def create(self, **kwargs):
        current = self.config['model']
        # A user-specified environment model is deliberately pinned. Stable
        # aliases (e.g. DeepSeek Flash) already roll forward at the provider.
        if (not self.config.get('auto_update_model', False) or os.getenv('VIDEO_AI_MODEL', '').strip()
                or 'ark.cn-beijing.volces.com' != (urlsplit(self.config['base_url']).hostname or '').lower()
                or _model_version(current) is None or kwargs.get('stream')):
            return self.client.chat.completions.create(**kwargs)
        with _LOCK:
            state = self._last_check(current)
            resolved = state.get('resolved_model') or current
            if (_model_version(resolved) and _model_version(resolved)[0] == _model_version(current)[0]):
                current = resolved
            try:
                checked_at = float(state.get('checked_at') or 0)
            except (ValueError, TypeError):
                checked_at = 0
            due = time.time() - checked_at >= CHECK_INTERVAL_SECONDS
            candidates = self._catalog(current, newer_only=True) if due else []
            if due:
                self._remember(current)
            attempted = set()
            for candidate in candidates:
                attempted.add(candidate)
                try:
                    response = self._request(candidate, kwargs)
                except APIError as error:
                    if getattr(error, 'status_code', None) in (401, 402, 429):
                        raise
                    continue
                except RuntimeError:
                    continue
                self._persist_working_model(candidate)
                self._remember(candidate)
                return response
            try:
                return self.client.chat.completions.create(**{**kwargs, 'model': current})
            except APIError as original:
                if not _is_closed_model(original):
                    raise
                candidates = self._catalog(current, newer_only=False)
                for candidate in candidates:
                    if len(attempted) >= 2:
                        break
                    if candidate in attempted:
                        continue
                    attempted.add(candidate)
                    try:
                        response = self._request(candidate, kwargs)
                    except APIError as error:
                        if getattr(error, 'status_code', None) in (401, 402, 429):
                            raise
                        continue
                    except RuntimeError:
                        continue
                    self._persist_working_model(candidate)
                    self._remember(candidate)
                    return response
                raise original
