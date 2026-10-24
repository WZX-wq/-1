import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mysql.connector
from openpyxl import Workbook
from PIL import Image

from database_tool.mysql_read_tool import fetch_with_retry
from database_tool import material_download_tool, video_load_tool
from ffmpeg_tool.add_watermark_tool import add_watermark
from ffmpeg_tool import subtitles_audio_tool
from ffmpeg_tool import video_concat_tool
from sanong_generation import copywriter as sanong_copywriter
from worker.composite_video_worker import CompositeVideo
from worker import ai_worker


class TempOutputTests(unittest.TestCase):
    def test_speed_adjustment_writes_next_to_task_audio(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            root_path = Path(root)
            source_dir = root_path / "readonly_source"
            work_dir = root_path / "task_cache"
            source_dir.mkdir()
            work_dir.mkdir()
            video_path = source_dir / "ending.mp4"
            audio_path = work_dir / "voice.mp3"
            video_path.touch()
            audio_path.touch()

            commands = []
            with patch.object(subtitles_audio_tool, "get_audio_length", return_value=2), \
                    patch.object(subtitles_audio_tool, "get_video_length", return_value=1), \
                    patch.object(subtitles_audio_tool, "run_ffmpeg", side_effect=commands.append):
                result = subtitles_audio_tool.adjust_video_speed_from_audio_path(
                    str(audio_path), str(video_path)
                )

            self.assertEqual(Path(result).parent, work_dir.resolve())
            self.assertEqual(Path(commands[0][-1]), Path(result))
            self.assertIn("-y", commands[0])

    def test_audio_merge_uses_unique_list_and_cleans_it_after_failure(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            root_path = Path(root)
            audio_path = root_path / "voice.mp3"
            audio_path.write_bytes(b"audio")
            output_path = root_path / "merged.mp3"

            with patch.object(subtitles_audio_tool, "run_ffmpeg", side_effect=RuntimeError("merge failed")) as runner:
                with self.assertRaisesRegex(RuntimeError, "merge failed"):
                    subtitles_audio_tool.merge_audios([str(audio_path)], str(output_path))

            command = runner.call_args.args[0]
            list_path = Path(command[command.index("-i") + 1])
            self.assertIn("-y", command)
            self.assertNotEqual(list_path.name, "temp_audio_list.txt")
            self.assertFalse(list_path.exists())


class CompositeCompletenessTests(unittest.TestCase):
    def test_one_failed_segment_prevents_merge_and_success(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            root_path = Path(root)
            processed = root_path / "processed.mp4"
            processed.touch()
            worker = CompositeVideo(
                ["source1.mp4", "source2.mp4"],
                ["audio1.mp3", "audio2.mp3"],
                ["one.ass", "two.ass"],
                [],
                str(root_path / "final.mp4"),
                {"transitionNum": 0, "transitionTime": 0},
                max_workers=1,
            )
            worker._process_single_video = lambda args: (
                (0, str(processed), True, "")
                if args[0] == 0 else (1, "", False, "片段 2: 处理失败")
            )
            worker.composite_process = lambda *_args: self.fail("片段不完整时不应进入合并")

            errors = []
            finished = []
            worker.signals.errorOccurred.connect(errors.append)
            worker.signals.finished.connect(finished.append)
            worker.run()

            self.assertEqual(finished, [])
            self.assertEqual(len(errors), 1)
            self.assertIn("成功 1/2", errors[0])
            self.assertFalse(processed.exists())


class DatabaseRetryTests(unittest.TestCase):
    def test_read_query_retries_transient_connection_failure(self):
        cursor = unittest.mock.Mock()
        cursor.fetchone.return_value = (123,)
        connection = unittest.mock.Mock()
        connection.cursor.return_value = cursor
        connection.is_connected.return_value = True

        with patch(
            "database_tool.mysql_read_tool.mysql.connector.connect",
            side_effect=[mysql.connector.Error("temporary"), connection],
        ) as connect, patch("database_tool.mysql_read_tool.time.sleep"):
            result = fetch_with_retry({}, "SELECT 1", operation_name="测试查询")

        self.assertEqual(result, (123,))
        self.assertEqual(connect.call_count, 2)
        cursor.execute.assert_called_once_with("SELECT 1", ())


class MaterialDownloadTests(unittest.TestCase):
    def test_download_retries_transient_server_errors(self):
        failed_response = unittest.mock.Mock(status_code=502)
        successful_response = unittest.mock.Mock(status_code=200)
        successful_response.iter_content.return_value = [b'video']
        failed_session = unittest.mock.MagicMock()
        failed_session.__enter__.return_value = failed_session
        failed_session.get.return_value = failed_response
        successful_session = unittest.mock.MagicMock()
        successful_session.__enter__.return_value = successful_session
        successful_session.get.return_value = successful_response

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root, \
                patch.object(
                    material_download_tool.requests,
                    'Session',
                    side_effect=[failed_session, successful_session],
                ) as session_class, \
                patch.object(material_download_tool.time, 'sleep'), \
                patch.object(material_download_tool.requests.adapters, 'HTTPAdapter') as adapter_class:
            result = material_download_tool.download_to_cache(
                'http://example/video.mp4', str(Path(root) / 'video.mp4'), '测试素材'
            )

        self.assertTrue(result)
        self.assertEqual(session_class.call_count, 2)
        retry_policy = adapter_class.call_args.kwargs['max_retries']
        self.assertEqual(retry_policy.total, 1)

    def test_private_material_server_bypasses_system_proxy(self):
        response = unittest.mock.Mock(status_code=200)
        response.iter_content.return_value = [b'video']
        session = unittest.mock.MagicMock()
        session.__enter__.return_value = session
        session.get.return_value = response

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root, \
                patch.object(material_download_tool.requests, 'Session', return_value=session):
            result = material_download_tool.download_to_cache(
                'http://100.122.91.10:8991/video.mp4',
                str(Path(root) / 'video.mp4'),
                '测试素材',
            )

        self.assertTrue(result)
        self.assertIs(session.trust_env, False)

    def test_afr_material_is_downloaded_when_not_cached(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root, \
                patch.object(video_load_tool.os, "getcwd", return_value=root), \
                patch.object(video_load_tool, "get_video_url", return_value="http://example/video.mp4"), \
                patch.object(video_load_tool, "download_to_cache", return_value=True), \
                patch.object(video_load_tool, "get_video_resolution", return_value=(1080, 1920)):
            result = video_load_tool.download_afr_video(123)

        self.assertTrue(result.endswith("123.mp4"))

    def test_regular_material_returns_path_for_non_target_resolution(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root, \
                patch.object(video_load_tool.os, "getcwd", return_value=root), \
                patch.object(video_load_tool, "get_video_url", return_value="http://example/video.mp4"), \
                patch.object(video_load_tool, "download_to_cache", return_value=True), \
                patch.object(video_load_tool, "get_video_resolution", return_value=(1280, 720)):
            result = video_load_tool.download_video(456, 0)

        self.assertTrue(result.endswith("456.mp4"))

    def test_unreadable_cached_material_is_removed_and_downloaded_again(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            cache_dir = Path(root) / "cacheVideo"
            cache_dir.mkdir()
            cached_file = cache_dir / "789.mp4"
            cached_file.write_bytes(b"incomplete")

            def download(_url, path, _name, auth=None):
                Path(path).write_bytes(b"complete")
                return True

            with patch.object(video_load_tool.os, "getcwd", return_value=root), \
                    patch.object(video_load_tool, "get_video_url", return_value="http://example/video.mp4"), \
                    patch.object(video_load_tool, "download_to_cache", side_effect=download) as downloader, \
                    patch.object(video_load_tool, "get_video_resolution", side_effect=[None, (640, 360)]):
                result = video_load_tool.download_video(789, 1)

            self.assertEqual(result, str(cached_file))
            self.assertEqual(downloader.call_count, 1)

    def test_word_image_canvas_is_vertical_hd_and_source_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            root_path = Path(root)
            source = root_path / "source.webp"
            watermark = root_path / "watermark.png"
            output = root_path / "output.png"
            Image.new("RGB", (300, 416), "blue").save(source)
            Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(watermark)

            add_watermark(str(source), str(watermark), str(output), (0, 0), (10, 10))

            self.assertTrue(source.exists())
            with Image.open(output) as result:
                self.assertEqual(result.size, (1080, 1920))


class MaterialCandidateFilterTests(unittest.TestCase):
    def tearDown(self):
        video_load_tool._material_candidate_cache.clear()
        video_load_tool._material_index_loaded = False
        video_load_tool._material_db_retry_after = 0

    def test_secondary_tag_filters_first_query_candidates_without_database(self):
        candidates = [
            {'id': 1, 'tags': '三清山_云海_日出'},
            {'id': 2, 'tags': '三清山_索道'},
        ]
        video_load_tool._cache_material_candidates(candidates)

        with patch.object(video_load_tool, '_get_videos_by_keyword_once') as database_query:
            result = video_load_tool.get_videos_by_keyword(
                '云海', 0, '', [1, 2], 5, 20, '普通素材'
            )

        self.assertEqual([video['id'] for video in result], [1])
        database_query.assert_not_called()

    def test_secondary_tag_uses_database_when_candidate_is_not_cached(self):
        with patch.object(
                video_load_tool,
                '_get_videos_by_keyword_once',
                return_value=[{'id': 3, 'tags': '三清山_云海'}]
        ) as database_query:
            result = video_load_tool.get_videos_by_keyword(
                '云海', 0, '', [3], 5, 20, '普通素材'
            )

        self.assertEqual([video['id'] for video in result], [3])
        database_query.assert_called_once()

    def test_offline_query_uses_persisted_index_and_existing_local_video(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            cache_dir = root_path / 'cacheVideo'
            cache_dir.mkdir()
            (cache_dir / '301.mp4').write_bytes(b'local-video')
            (cache_dir / '302.mp4').write_bytes(b'local-video')
            (root_path / 'material_index.json').write_text(
                '[{"id":301,"tags":"三清山_云海","city":"上饶",'
                '"screen":0,"duration":8,"material_category":"普通素材"},'
                '{"id":302,"tags":"婺源_油菜花","city":"上饶",'
                '"screen":0,"duration":8,"material_category":"普通素材"}]',
                encoding='utf-8',
            )
            with patch.object(video_load_tool.os, 'getcwd', return_value=str(root_path)), \
                    patch.object(video_load_tool, '_get_videos_by_keyword_1_once', return_value=None), \
                    patch.object(video_load_tool.time, 'sleep'):
                result = video_load_tool.get_videos_by_keyword_1(
                    '云海', 0, '上饶', 8, 3, '普通素材'
                )

        self.assertEqual([video['id'] for video in result], [301])
        self.assertFalse(result[0].get('local_only', False))

    def test_unindexed_local_videos_are_an_explicit_offline_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            cache_dir = root_path / 'cacheVideo'
            cache_dir.mkdir()
            (cache_dir / '401.mp4').write_bytes(b'local-video')
            with patch.object(video_load_tool.os, 'getcwd', return_value=str(root_path)), \
                    patch.object(video_load_tool, '_get_videos_by_keyword_1_once', return_value=None), \
                    patch.object(video_load_tool.time, 'sleep'):
                result = video_load_tool.get_videos_by_keyword_1(
                    '没有索引的标签', 0, '', 8, 3, '普通素材'
                )

        self.assertEqual([video['id'] for video in result], [401])
        self.assertTrue(result[0]['local_only'])

    def test_valid_cached_video_does_not_require_database_download_url(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            cache_dir = root_path / 'cacheVideo'
            cache_dir.mkdir()
            cached_video = cache_dir / '501.mp4'
            cached_video.write_bytes(b'local-video')
            with patch.object(video_load_tool.os, 'getcwd', return_value=str(root_path)), \
                    patch.object(video_load_tool, 'get_video_resolution', return_value=(1080, 1920)), \
                    patch.object(video_load_tool, 'get_video_url') as get_url:
                result = video_load_tool.download_video(501, 0)

        self.assertEqual(result, str(cached_video))
        get_url.assert_not_called()


class SanongGenerationTests(unittest.TestCase):
    def test_material_worker_reports_empty_copywriting_instead_of_skipping(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            title_file = Path(root) / "titles.xlsx"
            workbook = Workbook()
            workbook.active["B2"] = "农村宅基地政策"
            workbook.save(title_file)
            errors = []

            with patch.object(sanong_copywriter, "generate_strategy_content", return_value=[]), \
                    patch.object(sanong_copywriter, "write_arrays_to_excel") as write_excel:
                worker = ai_worker.AiDisposeMaterialStrategyTitle(str(title_file), "三农", 654)
                worker.signals.errorOccurred.connect(errors.append)
                worker.run()

            self.assertEqual(len(errors), 1)
            self.assertIn("文案生成失败", errors[0])
            write_excel.assert_not_called()

    def test_material_worker_writes_labels_and_updates_database(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            title_file = Path(root) / "titles.xlsx"
            workbook = Workbook()
            workbook.active["B2"] = "闲置土地如何利用"
            workbook.save(title_file)

            writes = []

            def capture_write(path, values):
                writes.append((Path(path), list(values)))

            with patch.object(
                    sanong_copywriter,
                    "generate_strategy_content",
                    return_value=["开场", "介绍闲置土地利用方法"],
            ), patch.object(
                    sanong_copywriter,
                    "generate_topics",
                    return_value=["土地利用", "农业政策"],
            ), patch.object(
                    sanong_copywriter,
                    "generate_material_tags",
                    side_effect=[["闲置土地", "土地利用"], ["农业政策"]],
            ), patch.object(sanong_copywriter, "segment_title", return_value="闲置土地如何利用"), \
                    patch.object(sanong_copywriter, "write_arrays_to_excel", side_effect=capture_write), \
                    patch.object(sanong_copywriter, "update_video_title_info", return_value=True) as update_info:
                worker = ai_worker.AiDisposeMaterialStrategyTitle(str(title_file), "三农", 321)
                worker.run()

            self.assertEqual([path.name for path, _values in writes], ["titles_copy.xlsx", "titles_label.xlsx"])
            self.assertEqual(writes[0][1][0], "闲置土地如何利用")
            self.assertEqual(writes[1][1], ["闲置土地,土地利用", "农业政策"])
            update_info.assert_called_once_with(
                321,
                "闲置土地如何利用&&土地利用,农业政策,三农&&开场&&介绍闲置土地利用方法",
                "闲置土地,土地利用&&农业政策",
            )

    def test_afr_keyword_query_is_scoped_to_sanong_materials(self):
        cursor = unittest.mock.Mock()
        cursor.fetchall.return_value = [{"id": 7, "tags": "土地利用"}]
        connection = unittest.mock.Mock()
        connection.is_connected.return_value = True
        connection.cursor.return_value = cursor

        with patch.object(video_load_tool.mysql.connector, "connect", return_value=connection):
            result = video_load_tool._get_afr_videos_by_keyword_once("土地利用", 0, 8, 20)

        self.assertEqual(result, [{"id": 7, "tags": "土地利用"}])
        query, params = cursor.execute.call_args.args
        self.assertIn("material_application = '三农素材'", query)
        self.assertIn("screen = %s", query)
        self.assertEqual(params, ("%土地利用%", 0, 8, 20, 8, 20))


class VideoConcatFallbackTests(unittest.TestCase):
    def test_multithread_merge_falls_back_after_no_progress(self):
        failed = {"success": False, "segment_index": 0, "error": "failed"}
        with patch.object(video_concat_tool, "_process_segment_multithread", return_value=failed), \
                patch.object(video_concat_tool, "_concatenate_videos_single_thread", return_value="fallback") as fallback:
            with patch("builtins.print"):
                result = video_concat_tool._concatenate_videos_multithread_sequential(
                    ["one.mp4", "two.mp4"], "output.mp4", "0", 1.0,
                    {"recommended_threads": 2},
                )

        self.assertEqual(result, "fallback")
        fallback.assert_called_once()


class CoverMergeTests(unittest.TestCase):
    def test_cover_merge_keeps_all_silent_video_segments(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory(dir=original_cwd) as root:
            root_path = Path(root)
            clips = []
            for index, color in enumerate(('red', 'blue')):
                clip = root_path / f'{index}.mp4'
                subprocess.run(
                    ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color={color}:s=320x240:d=1',
                     '-an', '-c:v', 'libx264', str(clip)],
                    check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                clips.append(str(clip))
            try:
                os.chdir(root_path)
                merged = video_load_tool.merge_videos(clips, 'silent_segments')
                duration = video_load_tool.get_video_duration(merged)
            finally:
                os.chdir(original_cwd)

        self.assertAlmostEqual(duration, 2.0, delta=0.2)


class AutoGenerateGuardTests(unittest.TestCase):
    def test_runtime_asset_path_falls_back_to_pyinstaller_bundle(self):
        import main

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            root_path = Path(root)
            executable_dir = root_path / "release"
            bundle_dir = root_path / "bundle"
            executable_dir.mkdir()
            (bundle_dir / "soft_pic").mkdir(parents=True)
            bundled_icon = bundle_dir / "tb.ico"
            bundled_icon.write_bytes(b"icon")

            with patch.object(main.sys, "frozen", True, create=True), \
                    patch.object(main.sys, "executable", str(executable_dir / "main.exe")), \
                    patch.object(main.sys, "_MEIPASS", str(bundle_dir), create=True):
                self.assertEqual(main.runtime_asset_path("tb.ico"), bundled_icon)

    def test_upload_accounts_are_not_queried_when_upload_is_disabled(self):
        import main

        checkbox = unittest.mock.Mock()
        checkbox.isChecked.return_value = False
        window = unittest.mock.Mock(uploadCheckBox=checkbox, _auto_generation_active=False)

        with patch.object(main, 'get_account_by_name') as query:
            result = main.BatchAICutter.get_upload_accounts(window, '测试账号')

        self.assertEqual(result, [])
        query.assert_not_called()

    def test_generate_button_is_restored_after_unhandled_error(self):
        import main

        class Button:
            def __init__(self):
                self.states = []

            def setEnabled(self, enabled):
                self.states.append(enabled)

        class Window:
            autoGenerateButton = Button()
            logs = []

            def _auto_generate_impl(self):
                raise RuntimeError("boom")

            def add_log(self, message):
                self.logs.append(message)

        window = Window()
        main.BatchAICutter.auto_generate(window)

        self.assertEqual(window.autoGenerateButton.states, [False, True])
        self.assertIn("boom", window.logs[0])

    def test_packaged_startup_seeds_setting_next_to_executable(self):
        import json
        import main

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory(dir=original_cwd) as root:
            root_path = Path(root)
            executable_dir = root_path / "app"
            bundle_dir = root_path / "bundle"
            executable_dir.mkdir()
            bundle_dir.mkdir()
            (bundle_dir / "setting.txt").write_text(
                json.dumps({"title_set": {}, "part_title_set": {}}), encoding="utf-8"
            )
            try:
                with patch.object(main.sys, "frozen", True, create=True), \
                        patch.object(main.sys, "executable", str(executable_dir / "main.exe")), \
                        patch.object(main.sys, "_MEIPASS", str(bundle_dir), create=True):
                    main.setup_runtime_directory()
                self.assertEqual(Path.cwd(), executable_dir)
                self.assertTrue((executable_dir / "setting.txt").exists())
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
