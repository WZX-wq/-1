import json
import tempfile
import unittest
from pathlib import Path

from sanong_generation.config import (
    RunnerConfig,
    StartupConfigurationError,
    discover_accounts,
    validate_local_resources,
)


def write_runner_config(base_dir: Path, **overrides) -> Path:
    payload = {
        "screen": 0,
        "random_video_model": True,
        "create_upload_tasks": True,
        "max_consecutive_system_failures": 3,
        "output_dir": "output",
    }
    payload.update(overrides)
    config_path = base_dir / "sanong_runner.json"
    config_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return config_path


def create_required_layout(base_dir: Path) -> None:
    (base_dir / "setting.txt").write_text("{}", encoding="utf-8")
    account_dir = base_dir / "video_model_set"
    account_dir.mkdir()
    (account_dir / "测试账号.txt").write_text("{}", encoding="utf-8")
    ffmpeg_dir = base_dir / "ffmpeg-bin"
    ffmpeg_dir.mkdir()
    (ffmpeg_dir / "ffmpeg.exe").touch()
    (ffmpeg_dir / "ffprobe.exe").touch()


class RunnerConfigTests(unittest.TestCase):
    def test_relative_output_is_resolved_from_executable_directory(self):
        with tempfile.TemporaryDirectory() as root:
            base_dir = Path(root)
            config = RunnerConfig.load(write_runner_config(base_dir), base_dir)

            self.assertEqual(config.output_dir, base_dir / "output")
            self.assertEqual(config.ffmpeg_dir, base_dir / "ffmpeg-bin")

    def test_accounts_are_txt_stems_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as root:
            account_dir = Path(root)
            (account_dir / "乙.txt").write_text("{}", encoding="utf-8")
            (account_dir / "甲.txt").write_text("{}", encoding="utf-8")
            (account_dir / "ignore.json").write_text("{}", encoding="utf-8")

            self.assertEqual(discover_accounts(account_dir), ["乙", "甲"])

    def test_missing_background_music_is_a_startup_error(self):
        with tempfile.TemporaryDirectory() as root:
            base_dir = Path(root)
            create_required_layout(base_dir)
            (base_dir / "cacheMusic1").mkdir()
            config = RunnerConfig.load(write_runner_config(base_dir), base_dir)

            with self.assertRaisesRegex(StartupConfigurationError, "背景音乐"):
                validate_local_resources(config, ["测试账号"])

    def test_invalid_screen_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            base_dir = Path(root)

            with self.assertRaisesRegex(StartupConfigurationError, "screen"):
                RunnerConfig.load(write_runner_config(base_dir, screen=3), base_dir)


if __name__ == "__main__":
    unittest.main()
