import ast
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class FakeCompletions:
    def __init__(self, content='["开场", "正文"]'):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FullVersionAiConfigurationTests(unittest.TestCase):
    def test_legacy_function_names_use_configured_openai_compatible_endpoint(self):
        module = importlib.import_module("ai_tool.doubao_ai_production")
        completions = FakeCompletions()
        client_kwargs = {}

        def client_factory(**kwargs):
            client_kwargs.update(kwargs)
            return SimpleNamespace(chat=SimpleNamespace(completions=completions))

        with patch.dict(
            os.environ,
            {
                "VIDEO_AI_API_KEY": "test-key",
                "VIDEO_AI_BASE_URL": "https://api.deepseek.com",
                "VIDEO_AI_MODEL": "deepseek-flash",
            },
            clear=False,
        ), patch.object(module, "_client", return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )):
            configured = module.get_ai_config()
            result = module.douBao_ai_strategy_content("标题", "要求")

        self.assertEqual(result, ["开场", "正文"])
        self.assertEqual(configured["api_key"], "test-key")
        self.assertEqual(configured["base_url"], "https://api.deepseek.com")
        self.assertEqual(completions.kwargs["model"], "deepseek-flash")


class StartupImportTests(unittest.TestCase):
    def test_heavy_optional_modules_are_not_top_level_imports(self):
        with open("main.py", encoding="utf-8") as source_file:
            tree = ast.parse(source_file.read())
        top_level_imports = {
            alias.name
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("whisper", top_level_imports)
        self.assertNotIn("pandas", top_level_imports)

    def test_whisper_import_is_local_to_transcription_workflow(self):
        with open("main.py", encoding="utf-8") as source_file:
            source = source_file.read()
        self.assertIn("import whisper", source)
        self.assertIn("def get_copy_from_video", source)


class AutoGenerationFailureStateTests(unittest.TestCase):
    def test_three_system_errors_stop_auto_generation(self):
        import main

        class Loop:
            def quit(self):
                pass

        logs = []
        window = SimpleNamespace(
            error_flag=False,
            last_error_message="",
            _consecutive_system_failures=0,
            _stop_auto_generation=False,
            add_log=logs.append,
            loop=Loop(),
        )
        with patch.object(main.QApplication, "processEvents"):
            for _ in range(3):
                main.BatchAICutter.on_error_occurred(window, "InvalidEndpoint.ClosedEndpoint")

        self.assertTrue(window._stop_auto_generation)
        self.assertEqual(window._consecutive_system_failures, 3)
        self.assertTrue(any("连续 3 次系统错误" in message for message in logs))

    def test_memory_error_stops_and_explains_recovery(self):
        import main

        class Loop:
            def quit(self):
                pass

        logs = []
        window = SimpleNamespace(
            error_flag=False,
            last_error_message="",
            _consecutive_system_failures=0,
            _stop_auto_generation=False,
            add_log=logs.append,
            loop=Loop(),
        )
        with patch.object(main.QApplication, "processEvents"):
            main.BatchAICutter.on_error_occurred(window, MemoryError())

        self.assertTrue(window._stop_auto_generation)
        self.assertTrue(any("关闭其他程序" in message for message in logs))


if __name__ == "__main__":
    unittest.main()
