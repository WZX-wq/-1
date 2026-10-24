import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sanong_generation.ai_client import (
    generate_material_tags,
    generate_strategy_content,
    generate_topics,
)


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class SanongAiClientTests(unittest.TestCase):
    def setUp(self):
        configured = patch('sanong_generation.ai_client.get_ai_config', return_value={
            'api_key': 'test-key', 'base_url': 'https://api.deepseek.com', 'model': 'deepseek-flash',
        })
        configured.start()
        self.addCleanup(configured.stop)

    def test_uses_verified_deepseek_flash_model_and_parses_json(self):
        completions = FakeCompletions('```json\n["开场", "正文"]\n```')
        factory_kwargs = {}

        def client_factory(**kwargs):
            factory_kwargs.update(kwargs)
            return SimpleNamespace(
                chat=SimpleNamespace(completions=completions)
            )

        result = generate_strategy_content(
            "宅基地如何申请",
            "生成三农短视频文案",
            client_factory=client_factory,
        )

        self.assertEqual(result, ["开场", "正文"])
        self.assertEqual(completions.kwargs["model"], "deepseek-flash")
        self.assertEqual(
            completions.kwargs["extra_body"],
            {"thinking": {"type": "disabled"}},
        )
        self.assertEqual(factory_kwargs["base_url"], "https://api.deepseek.com")
        self.assertTrue(factory_kwargs["api_key"])

    def test_invalid_response_returns_empty_list(self):
        completions = FakeCompletions("不是 JSON")

        result = generate_strategy_content(
            "标题",
            "要求",
            client_factory=lambda **_kwargs: SimpleNamespace(
                chat=SimpleNamespace(completions=completions)
            ),
        )

        self.assertEqual(result, [])

    def test_generates_topics_and_general_material_tags(self):
        topic_completions = FakeCompletions('["农村政策", "土地承包"]')
        tag_completions = FakeCompletions('["承包地", "村集体", "五保户"]')

        topics = generate_topics(
            "五保户承包地政策说明",
            client_factory=lambda **_kwargs: SimpleNamespace(
                chat=SimpleNamespace(completions=topic_completions)
            ),
        )
        tags = generate_material_tags(
            "五保户供养承包地由谁耕种",
            "村集体可以依法协调代耕",
            client_factory=lambda **_kwargs: SimpleNamespace(
                chat=SimpleNamespace(completions=tag_completions)
            ),
        )

        self.assertEqual(topics, ["农村政策", "土地承包"])
        self.assertEqual(tags, ["承包地", "村集体", "五保户"])
        self.assertIn("发布话题", topic_completions.kwargs["messages"][0]["content"])
        self.assertIn("画面素材", tag_completions.kwargs["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
