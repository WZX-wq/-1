import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sanong_generation.errors import MediaGenerationError
from sanong_generation.media_core import (
    add_background_music,
    generate_audio_subtitles,
)
from worker.add_music_worker import AddMusicWorker


class MediaCoreTests(unittest.TestCase):
    def test_module_import_does_not_load_pyqt(self):
        script = (
            "import sys; import sanong_generation.media_core; "
            "assert not any(name.startswith('PyQt6') for name in sys.modules)"
        )
        subprocess.run([sys.executable, "-c", script], check=True)

    def test_generate_audio_subtitles_returns_expected_files(self):
        async def fake_generate(_api_type, output_dir, _text, index, _settings):
            Path(output_dir, f"temp_final_audio{index}.mp3").touch()
            Path(output_dir, f"temp_subtitle{index}.srt").touch()

        with tempfile.TemporaryDirectory() as root, patch(
            "sanong_generation.media_core.produce_audio_and_subtitles_to_path",
            side_effect=fake_generate,
        ):
            progress = []
            results = generate_audio_subtitles(
                ["第一段", "第二段"],
                {"api_type": 0},
                Path(root),
                progress.append,
            )

        self.assertEqual([item.audio_path.name for item in results], [
            "temp_final_audio0.mp3",
            "temp_final_audio1.mp3",
        ])
        self.assertEqual(len(progress), 2)

    def test_generate_audio_subtitles_cleans_partial_files_on_failure(self):
        async def fake_generate(_api_type, output_dir, _text, index, _settings):
            Path(output_dir, f"temp_final_audio{index}.mp3").touch()
            Path(output_dir, f"temp_subtitle{index}.srt").touch()
            if index == 1:
                raise RuntimeError("TTS service stopped")

        with tempfile.TemporaryDirectory() as root, patch(
            "sanong_generation.media_core.produce_audio_and_subtitles_to_path",
            side_effect=fake_generate,
        ):
            with self.assertRaisesRegex(MediaGenerationError, "第 2 段"):
                generate_audio_subtitles(
                    ["第一段", "第二段"],
                    {"api_type": 0},
                    Path(root),
                )

            self.assertEqual(list(Path(root).iterdir()), [])

    def test_add_background_music_returns_existing_output(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "final.mp4"
            with patch(
                "sanong_generation.media_core.add_bgm_to_video",
                side_effect=lambda *_args: output.touch(),
            ):
                result = add_background_music(
                    Path("input.mp4"), Path("music.mp3"), 100, 40, output
                )

            self.assertEqual(result, output)

    def test_add_background_music_raises_when_output_is_missing(self):
        with tempfile.TemporaryDirectory() as root, patch(
            "sanong_generation.media_core.add_bgm_to_video", return_value=None
        ):
            with self.assertRaisesRegex(MediaGenerationError, "背景音乐"):
                add_background_music(
                    Path("input.mp4"),
                    Path("music.mp3"),
                    100,
                    40,
                    Path(root) / "missing.mp4",
                )

    def test_add_music_worker_wraps_shared_core(self):
        worker = AddMusicWorker("in.mp4", "music.mp3", 100, 40, "out.mp4")
        finished = []
        errors = []
        worker.signals.finished.connect(finished.append)
        worker.signals.errorOccurred.connect(errors.append)

        with patch(
            "worker.add_music_worker.add_background_music",
            return_value=Path("out.mp4"),
        ) as add_music:
            worker.run()

        add_music.assert_called_once()
        self.assertEqual(finished, ["添加背景音乐完成"])
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
