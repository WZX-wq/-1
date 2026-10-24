"""Create a temporary private module for PyInstaller's embedded PYZ archive.

Opt-in via VIDEO_AI_EMBED_CONFIG. Generated modules must never be committed or
published: client-side credentials can be extracted from any portable program.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


MODULE_NAME = 'video_ai_embedded_config'


def create_private_ai_module(config_path: str):
    if not config_path:
        return None
    try:
        data = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
        settings = {key: str(data.get(key) or '').strip() for key in ('api_key', 'base_url', 'model')}
    except (OSError, ValueError, AttributeError) as error:
        raise RuntimeError('Cannot read private AI build configuration; no credentials were logged.') from None
    parsed = urlsplit(settings['base_url'])
    if (not all(settings.values()) or settings['api_key'].startswith(('在此填写', '你的', '请填写'))
            or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password):
        raise RuntimeError('Private AI build requires a valid key, HTTPS base URL and model.')
    settings['base_url'] = settings['base_url'].rstrip('/')
    settings['auto_update_model'] = data.get('auto_update_model', True) is True
    temporary = tempfile.TemporaryDirectory(prefix='video_ai_private_')
    try:
        # A build artifact in an OS temp folder, not a source-tree credential.
        (Path(temporary.name) / f'{MODULE_NAME}.py').write_text(
            '# Private build artifact. Do not publish.\nSETTINGS = ' + repr(settings) + '\n', encoding='utf-8'
        )
    except BaseException:
        temporary.cleanup()
        raise
    return temporary
