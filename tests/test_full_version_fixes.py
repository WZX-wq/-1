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
    def test_model_array_items_are_normalized_to_text(self):
        module = importlib.import_module("ai_tool.doubao_ai_production")

        self.assertEqual(
            module._normalize_text_list([
                "开场",
                {"word": "三清山"},
                {"text": "云海壮观"},
            ]),
            ["开场", "三清山", "云海壮观"],
        )

    def test_edge_voice_choice_is_preserved_when_loading_a_template(self):
        import main
        settings = {"voice_set": {"api_type": 0}}
        with patch.object(main, "load_voice_preferences", return_value={
            "api_type": 0, "random_voice": True,
        }):
            migrated = main.migrate_legacy_voice_setting(settings, "setting.txt")
        self.assertEqual(migrated["voice_set"]["api_type"], 0)
        self.assertTrue(migrated["voice_set"]["random_voice"])

    def test_rereading_setting_does_not_rewrite_or_force_another_provider(self):
        import main
        with patch.object(main.os.path, "exists", return_value=True), \
                patch("builtins.open", unittest.mock.mock_open(read_data='{"voice_set": {"api_type": 0}}')), \
                patch.object(main, "load_voice_preferences", return_value={"api_type": 0}), \
                patch.object(main, "write_dict_to_txt") as write_setting:
            reread = main.read_dict_from_txt("setting.txt")

        self.assertEqual(reread["voice_set"]["api_type"], 0)
        write_setting.assert_not_called()

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


class StructuredContentRecoveryTests(unittest.TestCase):
    def test_json_records_unwrap_nested_strings_and_lists(self):
        import main

        value = '[{"Day1": {"行程安排": "上午"}}, "{\\"Day2\\": {\\"行程安排\\": \\"下午\\"}}"]'
        records = main._normalize_json_records(value)

        self.assertEqual([list(record) for record in records], [["Day1"], ["Day2"]])

    def test_json_records_ignore_invalid_scalar_values(self):
        import main

        self.assertEqual(main._normalize_json_records('invalid text'), [])
        self.assertEqual(main._normalize_json_records(123), [])


class WatermarkErrorReportingTests(unittest.TestCase):
    def test_none_ffmpeg_stderr_is_safe_to_decode(self):
        from ffmpeg_tool import add_watermark_tool

        self.assertEqual(add_watermark_tool._decode_process_output(None), '')
        self.assertEqual(add_watermark_tool._decode_process_output(b'error'), 'error')


class StartupImportTests(unittest.TestCase):
    def test_auto_generation_pumps_ui_while_material_calls_run(self):
        import time
        from PyQt6.QtCore import QThreadPool, QTimer
        import main

        app = main.QApplication.instance() or main.QApplication([])
        window = SimpleNamespace(thread_pool=QThreadPool.globalInstance())
        ticks = []
        timer = QTimer()
        timer.setInterval(5)
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start()
        main._active_generation_window = window
        try:
            call = main._UiPumpedCall(lambda: (time.sleep(0.1), "complete")[1])
            result = call()
        finally:
            main._active_generation_window = None
            timer.stop()

        self.assertEqual(result, "complete")
        self.assertGreater(len(ticks), 0)

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

    def test_startup_update_check_uses_background_worker(self):
        source = open("main.py", encoding="utf-8").read()
        init_body = source[source.index("    def __init__(self):"):source.index("    def toggle_maximize")]
        self.assertIn("self.auto_check_update()", init_body)
        self.assertNotIn("check_for_updates()", init_body)
        self.assertIn("UpdateCheckWorker", source)


class VoiceSettingsLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        import main

        cls.app = QApplication.instance() or QApplication([])
        cls.main = main

    def test_edge_refresh_button_does_not_cover_test_controls(self):
        from PyQt6.QtWidgets import QWidget

        window = self.main.BatchAICutter.__new__(self.main.BatchAICutter)
        QWidget.__init__(window)
        window.setupUi(window)
        window._setup_tts_provider_ui()
        try:
            controls = (
                window.refreshEdgeVoiceListButton,
                window.label_82,
                window.testAudioLineEdit,
            )
            self.assertEqual(window.refreshEdgeVoiceListButton.width(), 72)
            for index, first in enumerate(controls):
                for second in controls[index + 1:]:
                    self.assertFalse(
                        first.geometry().intersects(second.geometry()),
                        f"{first.objectName()} overlaps {second.objectName()}",
                    )
        finally:
            window.close()
            window.deleteLater()


class AudioFailureTests(unittest.TestCase):
    def test_failed_tts_does_not_return_an_empty_success_path(self):
        from ffmpeg_tool import subtitles_audio_tool

        with patch.object(subtitles_audio_tool, "Communicate", side_effect=RuntimeError("endpoint closed")), \
                patch.object(subtitles_audio_tool.asyncio, "sleep"), \
                patch.object(subtitles_audio_tool.os.path, "exists", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "语音生成失败"):
                import asyncio
                asyncio.run(subtitles_audio_tool.generate_voice("测试", "missing.mp3"))

    def test_audio_pipeline_reports_missing_voice_before_ffprobe(self):
        from ffmpeg_tool import subtitles_audio_tool
        with patch.object(subtitles_audio_tool, "generate_voice", return_value=""), \
                patch.object(subtitles_audio_tool, "get_audio_length") as get_length:
            import asyncio
            with self.assertRaisesRegex(FileNotFoundError, "配音文件未生成"):
                asyncio.run(subtitles_audio_tool.produce_audio_and_subtitles_to_path(
                    0, ".", "测试", 0,
                    {"volume_value": 0, "audio_role": "voice", "speed_value": "+0%"},
                ))
            get_length.assert_not_called()

    def test_baidu_tts_rejects_non_audio_response(self):
        from ffmpeg_tool import subtitles_audio_tool

        response = SimpleNamespace(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"err_msg":"invalid token"}',
            json=lambda: {"err_msg": "invalid token"},
        )
        with patch.object(subtitles_audio_tool, "get_access_token", return_value="token"), \
                patch.object(subtitles_audio_tool.requests, "request", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "百度配音失败"):
                subtitles_audio_tool.bd_generate_voice("测试", "missing.mp3", 1, 5, 0, 0)


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
        with patch.object(main.QApplication, "processEvents"), \
                patch.object(main.QApplication, "instance", return_value=object()), \
                patch.object(main.QMessageBox, "warning") as warning:
            main.BatchAICutter.on_error_occurred(window, MemoryError())

        self.assertTrue(window._stop_auto_generation)
        self.assertTrue(any("关闭其他程序" in message for message in logs))
        warning.assert_called_once_with(window, '内存不足', main.MEMORY_EXHAUSTION_MESSAGE)


if __name__ == "__main__":
    unittest.main()
