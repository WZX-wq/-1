import os
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("SANONG_RELEASE_DIR"), "SANONG_RELEASE_DIR not set")
class SanongPackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = Path(os.environ["SANONG_RELEASE_DIR"])

    def test_release_directory_contains_mutable_runtime_resources(self):
        release = self.release
        self.assertTrue((release / "三农视频生成.exe").is_file())
        self.assertTrue((release / "sanong_runner.json").is_file())
        self.assertTrue((release / "setting.txt").is_file())
        self.assertTrue((release / "三农视频生成使用说明.txt").is_file())
        self.assertTrue((release / "tb.ico").is_file())
        self.assertTrue((release / "soft_pic" / "4.png").is_file())
        self.assertTrue((release / "soft_pic" / "cylogo.png").is_file())
        self.assertTrue(any((release / "video_model_set").glob("*.txt")))
        self.assertTrue(any((release / "cacheMusic1").glob("*.[mM][pP]3")))
        self.assertTrue(any((release / "cacheAFRVideo").glob("*.[mM][pP]4")))
        self.assertTrue(
            (release / "_internal" / "ffmpeg-bin" / "ffmpeg.exe").is_file()
        )
        self.assertTrue(
            (release / "_internal" / "ffmpeg-bin" / "ffprobe.exe").is_file()
        )

    def test_release_contains_gui_and_windows_runtimes(self):
        qt_root = self.release / "_internal" / "PyQt6" / "Qt6"
        self.assertTrue((qt_root / "bin" / "Qt6Core.dll").is_file())
        self.assertTrue((qt_root / "bin" / "Qt6Gui.dll").is_file())
        self.assertTrue((qt_root / "bin" / "Qt6Widgets.dll").is_file())
        self.assertTrue((qt_root / "plugins" / "platforms" / "qwindows.dll").is_file())
        for icu_name in ("icu.dll", "icuin.dll", "icuuc.dll"):
            self.assertTrue((qt_root / "bin" / icu_name).is_file())

        names = {
            path.name.lower()
            for path in self.release.rglob("*")
            if path.is_file()
        }
        for required in (
            "vcruntime140.dll",
            "vcruntime140_1.dll",
            "msvcp140.dll",
            "ucrtbase.dll",
            "python312.dll",
        ):
            self.assertIn(required, names)

        for forbidden_prefix in ("torch", "whisper", "torchaudio", "torchvision"):
            self.assertFalse(
                any(name.startswith(forbidden_prefix) for name in names),
                f"unexpected heavyweight runtime: {forbidden_prefix}",
            )


if __name__ == "__main__":
    unittest.main()
