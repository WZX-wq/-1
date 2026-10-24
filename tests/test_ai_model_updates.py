import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import httpx2 as httpx
except ImportError:
    import httpx
from openai import OpenAI

from ai_tool import runtime_config
from ai_tool.model_updates import _CACHE, compatible_models


OLD = 'doubao-seed-2-0-lite-260428'
NEW = 'doubao-seed-2-1-lite-260915'


def model(identifier, status=None, text=True):
    return {'id': identifier, 'object': 'model', 'created': 1, 'owned_by': 'bytedance',
            'status': status, 'modalities': {'output_modalities': ['text' if text else 'image']},
            'task_type': ['TextGeneration' if text else 'ImageGeneration']}


class ModelUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'video_ai_config.json'
        environment = patch.dict(os.environ, {
            'VIDEO_AI_CONFIG': str(self.path), 'VIDEO_AI_MODEL': '',
            'VIDEO_AI_API_KEY': '', 'VIDEO_AI_BASE_URL': '',
        })
        environment.start()
        self.addCleanup(environment.stop)
        _CACHE.clear()
        self.addCleanup(_CACHE.clear)
        runtime_config.save_ai_config({'api_key': 'test-secret', 'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
                                       'model': OLD, 'auto_update_model': True})

    def client(self, handler):
        def factory(**kwargs):
            kwargs['max_retries'] = 0
            client = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.addCleanup(client.close)
            return client
        return runtime_config.create_ai_client(factory)

    def response(self, requested_model):
        return httpx.Response(200, json={
            'id': 'test', 'object': 'chat.completion', 'created': 1, 'model': requested_model,
            'choices': [{'index': 0, 'finish_reason': 'stop',
                         'message': {'role': 'assistant', 'content': '["有效文案"]'}}],
        })

    def request(self, client):
        return client.chat.completions.create(model='ignored-legacy', messages=[{'role': 'user', 'content': '文案'}])

    def test_catalog_excludes_retired_preview_wrong_tier_and_non_text_models(self):
        entries = [model(NEW), model('doubao-seed-2-2-pro-261020'), model('doubao-seed-2-2-lite-261020', 'Shutdown'),
                   model('doubao-seed-2-2-lite-261019', 'Retiring'), model('doubao-seed-2-2-lite-261018', text=False),
                   model('doubao-seed-2-3-lite-preview-261020'), model(OLD)]
        self.assertEqual(compatible_models(entries, OLD, newer_only=True), [NEW])
        self.assertEqual(compatible_models(entries, 'ep-custom-id', newer_only=False), [])

    def test_new_model_is_persisted_only_after_success_and_catalog_is_daily(self):
        calls = []
        def handle(request):
            calls.append((request.method, request.url.path))
            if request.method == 'GET':
                return httpx.Response(200, json={'object': 'list', 'data': [model(NEW)]})
            return self.response(json.loads(request.content)['model'])
        response = self.request(self.client(handle))
        self.assertEqual(response.model, NEW)
        self.assertEqual(runtime_config.get_ai_config()['model'], NEW)
        self.request(self.client(handle))
        self.assertEqual(sum(method == 'GET' for method, _ in calls), 1)
        state = self.path.with_name('video_ai_model_state.json').read_text(encoding='utf-8')
        self.assertNotIn('test-secret', state)

    def test_candidate_failure_keeps_working_model_and_existing_config(self):
        def handle(request):
            if request.method == 'GET':
                return httpx.Response(200, json={'object': 'list', 'data': [model(NEW)]})
            requested = json.loads(request.content)['model']
            if requested == NEW:
                return httpx.Response(403, json={'error': {'code': 'ModelNotOpen', 'message': 'not enabled'}})
            return self.response(requested)
        self.assertEqual(self.request(self.client(handle)).model, OLD)
        self.assertEqual(runtime_config.get_ai_config()['model'], OLD)

    def test_closed_current_model_refreshes_even_after_daily_check(self):
        catalog_calls = []
        def handle(request):
            if request.method == 'GET':
                catalog_calls.append(True)
                entries = [] if len(catalog_calls) == 1 else [model(NEW)]
                return httpx.Response(200, json={'object': 'list', 'data': entries})
            requested = json.loads(request.content)['model']
            if requested == OLD:
                return httpx.Response(400, json={'error': {'code': 'InvalidEndpoint.ClosedEndpoint', 'message': 'closed'}})
            return self.response(requested)
        self.assertEqual(self.request(self.client(handle)).model, NEW)
        self.assertEqual(len(catalog_calls), 2)
        self.assertEqual(runtime_config.get_ai_config()['model'], NEW)

    def test_insufficient_balance_does_not_switch_models(self):
        posted = []
        def handle(request):
            if request.method == 'GET':
                return httpx.Response(200, json={'object': 'list', 'data': []})
            posted.append(json.loads(request.content)['model'])
            return httpx.Response(402, json={'error': {'code': 'insufficient_quota', 'message': 'Insufficient Balance'}})
        with self.assertRaisesRegex(runtime_config.AIServiceError, '余额或额度不足'):
            self.request(self.client(handle))
        self.assertEqual(posted, [OLD])
        self.assertEqual(runtime_config.get_ai_config()['model'], OLD)

    def test_disabled_updates_never_query_catalog(self):
        settings = runtime_config.get_ai_config()
        settings['auto_update_model'] = False
        runtime_config.save_ai_config(settings)
        methods = []
        def handle(request):
            methods.append(request.method)
            return self.response(json.loads(request.content)['model'])
        self.request(self.client(handle))
        self.assertEqual(methods, ['POST'])

    def test_catalog_outage_keeps_current_model(self):
        def handle(request):
            if request.method == 'GET':
                return httpx.Response(503, json={'error': {'message': 'unavailable'}})
            return self.response(json.loads(request.content)['model'])
        self.assertEqual(self.request(self.client(handle)).model, OLD)


if __name__ == '__main__':
    unittest.main()
