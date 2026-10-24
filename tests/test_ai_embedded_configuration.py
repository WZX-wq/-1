import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_tool import runtime_config
from tools.private_ai_build import create_private_ai_module, MODULE_NAME


class EmbeddedConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'video_ai_config.json'
        self.settings = {'api_key': 'fake-private-test-key', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
                         'model': 'doubao-seed-2-0-lite-260428', 'auto_update_model': True}
        environment = patch.dict(os.environ, {'VIDEO_AI_CONFIG': str(self.path), 'VIDEO_AI_API_KEY': '',
                                             'VIDEO_AI_BASE_URL': '', 'VIDEO_AI_MODEL': ''})
        environment.start()
        self.addCleanup(environment.stop)
        embedded = patch.dict(sys.modules, {MODULE_NAME: SimpleNamespace(SETTINGS=self.settings)})
        embedded.start()
        self.addCleanup(embedded.stop)
        frozen = patch.object(sys, 'frozen', True, create=True)
        frozen.start()
        self.addCleanup(frozen.stop)

    def test_private_build_needs_no_external_key_or_config(self):
        self.assertFalse(self.path.exists())
        self.assertEqual(runtime_config.get_ai_config(), self.settings)

    def test_public_source_does_not_load_private_defaults(self):
        with patch.object(sys, 'frozen', False):
            with self.assertRaisesRegex(RuntimeError, '未配置'):
                runtime_config.get_ai_config()

    def test_embedded_key_is_not_forwarded_to_another_provider(self):
        with patch.dict(os.environ, {'VIDEO_AI_BASE_URL': 'https://example.com/v1'}):
            with self.assertRaisesRegex(RuntimeError, '未配置'):
                runtime_config.get_ai_config()

    def test_user_configuration_overrides_private_defaults(self):
        override = {'api_key': 'fake-replacement', 'base_url': 'https://api.deepseek.com',
                    'model': 'deepseek-flash', 'auto_update_model': False}
        runtime_config.save_ai_config(override)
        self.assertEqual(runtime_config.get_ai_config(), override)

    def test_automatic_model_update_never_writes_embedded_key_to_disk(self):
        from ai_tool.model_updates import ModelAutoUpdater
        updated = 'doubao-seed-2-1-lite-260915'
        ModelAutoUpdater(None, runtime_config.get_ai_config())._persist_working_model(updated)
        self.assertEqual(runtime_config.get_ai_config()['model'], updated)
        self.assertEqual(runtime_config.get_ai_config()['api_key'], self.settings['api_key'])
        saved = self.path.read_text(encoding='utf-8')
        self.assertNotIn('fake-private-test-key', saved)
        self.assertNotIn('api_key', json.loads(saved))

    def test_build_module_is_opt_in_temporary_and_matches_settings(self):
        self.assertIsNone(create_private_ai_module(''))
        runtime_config.save_ai_config(self.settings)
        generated = create_private_ai_module(str(self.path))
        module_path = Path(generated.name) / f'{MODULE_NAME}.py'
        spec = importlib.util.spec_from_file_location('private_build_test', module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.SETTINGS, self.settings)
        generated.cleanup()
        self.assertFalse(module_path.exists())


if __name__ == '__main__':
    unittest.main()
