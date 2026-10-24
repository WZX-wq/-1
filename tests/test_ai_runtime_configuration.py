import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import httpx2 as httpx
except ImportError:
    import httpx
from openai import OpenAI
from openpyxl import Workbook

from ai_tool import runtime_config
from ai_tool import ai_text_production, doubao_ai_production
from runtime_errors import is_system_generation_error


class AiRuntimeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'video_ai_config.json'
        self.environ = patch.dict(os.environ, {
            'VIDEO_AI_CONFIG': str(self.path), 'VIDEO_AI_API_KEY': '',
            'VIDEO_AI_BASE_URL': '', 'VIDEO_AI_MODEL': '',
        })
        self.environ.start()
        self.addCleanup(self.environ.stop)

    def save(self, model='configured-model'):
        runtime_config.save_ai_config({
            'api_key': 'test-secret-not-a-real-key',
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
            'model': model,
            'auto_update_model': False,
        })

    def factory(self, requests, status=200, body=None):
        def handle(request):
            requests.append(json.loads(request.content))
            return httpx.Response(status, json=body or {
                'id': 'test-completion', 'object': 'chat.completion', 'created': 0,
                'model': 'configured-model',
                'choices': [{'index': 0, 'finish_reason': 'stop',
                             'message': {'role': 'assistant', 'content': '["开场", "正文"]'}}],
            })

        def create(**kwargs):
            kwargs['max_retries'] = 0
            client = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle)))
            self.addCleanup(client.close)
            return client
        return create

    def test_both_legacy_workers_send_saved_model_and_can_change_without_restart(self):
        sent = []
        self.save('first-model')
        factory = self.factory(sent)
        with patch.object(doubao_ai_production, '_client', side_effect=lambda: runtime_config.create_ai_client(factory)), \
                patch.object(ai_text_production, 'create_ai_client', side_effect=lambda: runtime_config.create_ai_client(factory)):
            self.assertEqual(doubao_ai_production.douBao_ai_strategy_content('标题', '要求'), ['开场', '正文'])
            self.save('second-model')
            self.assertEqual(ai_text_production.deepseek_ai_strategy_topic('文案'), ['开场', '正文'])
        self.assertEqual([payload['model'] for payload in sent], ['first-model', 'second-model'])
        self.assertTrue(all(payload['thinking'] == {'type': 'disabled'} for payload in sent))

    def test_closed_endpoint_and_balance_are_distinct_actionable_system_errors(self):
        self.save()
        for status, code, message, expected in (
            (400, 'InvalidEndpoint.ClosedEndpoint', 'endpoint closed', '模型端点已关闭'),
            (402, 'insufficient_quota', 'Insufficient Balance', '余额或额度不足'),
            (401, 'invalid_api_key', 'Invalid API key', '密钥无效'),
        ):
            with self.subTest(status=status):
                client = runtime_config.create_ai_client(self.factory([], status, {
                    'error': {'code': code, 'message': message, 'type': 'api_error'},
                }))
                with self.assertRaises(runtime_config.AIServiceError) as raised:
                    client.chat.completions.create(model='old', messages=[{'role': 'user', 'content': 'test'}])
                self.assertIn(expected, str(raised.exception))
                self.assertNotIn('test-secret', str(raised.exception))
                self.assertTrue(is_system_generation_error(raised.exception))

    def test_saved_config_round_trip_and_environment_override(self):
        self.save()
        self.assertEqual(runtime_config.get_ai_config()['model'], 'configured-model')
        with patch.dict(os.environ, {'VIDEO_AI_MODEL': 'environment-model'}):
            self.assertEqual(runtime_config.get_ai_config()['model'], 'environment-model')

    def test_placeholder_and_invalid_json_fail_before_network(self):
        with self.assertRaisesRegex(RuntimeError, '有效'):
            runtime_config.save_ai_config({'api_key': '在此填写 AI 服务密钥', 'base_url': 'https://example.com', 'model': 'test'})
        self.path.write_text('{invalid', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, '配置文件无法读取'):
            runtime_config.get_ai_config()

    def test_ai_settings_save_button_persists_values(self):
        import main
        from PyQt6.QtWidgets import QApplication, QLineEdit

        app = QApplication.instance() or QApplication([])
        window = SimpleNamespace(
            apiBaseUrlLineEdit=QLineEdit('https://ark.cn-beijing.volces.com/api/v3'),
            aiModelNameLineEdit=QLineEdit('saved-in-ui'),
            apiKeyLineEdit=QLineEdit('test-secret-not-a-real-key'),
            aiAutoUpdateCheckBox=SimpleNamespace(isChecked=lambda: True),
            load_ai_settings=lambda: None, add_log=lambda _message: None,
        )
        with patch.object(main.QMessageBox, 'information'), patch.object(main.QMessageBox, 'warning') as warning:
            main.BatchAICutter.save_ai_settings(window)
        warning.assert_not_called()
        self.assertEqual(runtime_config.get_ai_config()['model'], 'saved-in-ui')
        self.assertIsNotNone(app)


class WorkbookImportRegressionTests(unittest.TestCase):
    def test_ai_worker_reads_a_real_workbook_without_recursion(self):
        from worker.ai_worker import _read_excel
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'titles.xlsx'
            workbook = Workbook()
            workbook.active.append(['编号', '标题'])
            workbook.active.append([1, '上饶旅游攻略'])
            workbook.save(path)
            rows = _read_excel(path)
            self.assertEqual(rows.iloc[0, 1], '上饶旅游攻略')


if __name__ == '__main__':
    unittest.main()
