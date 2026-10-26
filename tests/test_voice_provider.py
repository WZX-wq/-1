import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ffmpeg_tool.add_music_tool import add_bgm_to_video
from ffmpeg_tool.subtitles_audio_tool import choose_random_audio_voice
from sanong_generation.composer import build_audio_settings
from video_work import cleanup_video_work, create_video_work_paths
from voice_catalog import BAIDU_VOICE_ROLE_IDS


class VoiceProviderTests(unittest.TestCase):
    def test_edge_and_baidu_are_the_only_supported_voice_providers(self):
        edge = build_audio_settings({"voice_set": {
            "api_type": 0, "role_0": 1, "role_0_name": "zh-CN-XiaoxiaoNeural",
            "spd_0": -4, "vol_0": 8,
        }})
        self.assertEqual(edge["api_type"], 0)
        self.assertEqual(edge["audio_role"], "zh-CN-XiaoxiaoNeural")
        self.assertEqual(edge["speed_value"], "-4%")

        baidu = build_audio_settings({"voice_set": {
            "api_type": 1, "role_1": 2, "spd_1": 6, "vol_1": 7, "pit_1": 4,
        }})
        self.assertEqual(baidu["api_type"], 1)
        self.assertEqual(baidu["audio_role"], BAIDU_VOICE_ROLE_IDS[2])
        self.assertEqual(baidu["speed_value"], 6)

    def test_removed_provider_setting_migrates_to_baidu(self):
        settings = build_audio_settings({"voice_set": {
            "api_type": 2, "role_1": 1, "random_voice": False,
        }})
        self.assertEqual(settings["api_type"], 1)
        self.assertEqual(settings["audio_role"], BAIDU_VOICE_ROLE_IDS[1])
        self.assertFalse(settings["random_voice"])

    def test_random_edge_voice_is_selected_once_for_video_and_speakers(self):
        with patch(
            "ffmpeg_tool.subtitles_audio_tool.load_voice_preferences",
            return_value={"edge_voice_options": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"]},
        ):
            selections = iter(("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"))
            settings = choose_random_audio_voice(
                {"api_type": 0, "random_voice": True},
                chooser=lambda _items: next(selections),
            )

        self.assertEqual(settings["audio_role"], "zh-CN-YunxiNeural")
        self.assertEqual(settings["speaker_roles"]["A"], "zh-CN-XiaoxiaoNeural")
        self.assertEqual(settings["speaker_roles"]["B"], "zh-CN-YunxiNeural")
        self.assertEqual(choose_random_audio_voice(settings), settings)

    def test_random_baidu_voice_uses_supported_voice_ids(self):
        settings = choose_random_audio_voice(
            {"api_type": 1, "random_voice": True},
            chooser=lambda options: options[-1],
        )
        self.assertEqual(settings["audio_role"], BAIDU_VOICE_ROLE_IDS[-1])
        self.assertEqual(settings["api_type"], 1)

    def test_video_stages_are_outside_public_output_and_cleaned(self):
        with tempfile.TemporaryDirectory() as root:
            stage, final, work_dir = create_video_work_paths(root, "A_title_0.mp4")
            self.assertEqual(Path(stage).parent, work_dir)
            self.assertEqual(Path(final), Path(root) / "A_title.mp4")
            self.assertFalse((Path(root) / "A_title_0.mp4").exists())
            Path(stage).touch()
            cleanup_video_work(work_dir)
            self.assertFalse(work_dir.exists())
            self.assertFalse((Path(root) / ".video_work").exists())

    def test_bgm_ffmpeg_failure_is_reported_and_no_output_is_left(self):
        class FailedProcess:
            returncode = 1
            stdout = ""
            stderr = "invalid audio stream"

        with tempfile.TemporaryDirectory() as root:
            input_video = Path(root) / "input.mp4"
            music = Path(root) / "music.mp3"
            output = Path(root) / "with_bgm.mp4"
            input_video.write_bytes(b"video")
            music.write_bytes(b"audio")
            with patch(
                "ffmpeg_tool.add_music_tool.subprocess.run",
                return_value=FailedProcess(),
            ):
                with self.assertRaisesRegex(RuntimeError, "FFmpeg 添加背景音乐失败"):
                    add_bgm_to_video(input_video, music, 100, 40, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
