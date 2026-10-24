import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from sanong_generation.composer import (
    DefaultMediaBackend,
    PreparedMaterial,
    PreparedSegment,
    SanongComposer,
    _append_xlsx,
    build_audio_settings,
    select_local_sanong_material,
)
from sanong_generation.errors import TitleGenerationError


def write_excel_row(path: Path, values) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    for column, value in enumerate(values, start=1):
        sheet.cell(row=1, column=column, value=value)
    workbook.save(path)
    return path


class SanongMaterialSelectionTests(unittest.TestCase):
    def test_selects_an_unused_mp4_from_local_cache_only(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = Path(root) / "cacheAFRVideo"
            cache_dir.mkdir()
            (cache_dir / "8.mp4").touch()
            (cache_dir / "9.mp4").touch()
            (cache_dir / "ignore.txt").touch()

            selected = select_local_sanong_material(
                cache_dir,
                used_ids={8},
                chooser=lambda candidates: candidates[0],
            )

        self.assertEqual(selected.material_id, 9)
        self.assertEqual(selected.video_path.name, "9.mp4")

    def test_local_cache_exhaustion_fails_without_remote_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = Path(root) / "cacheAFRVideo"
            cache_dir.mkdir()
            (cache_dir / "8.mp4").touch()

            with self.assertRaisesRegex(TitleGenerationError, "本地三农素材不足"):
                select_local_sanong_material(cache_dir, used_ids={8})

    def test_default_backend_cuts_selected_local_material(self):
        logs = []
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            cache_dir = root_path / "cacheAFRVideo"
            cache_dir.mkdir()
            source = cache_dir / "12.mp4"
            source.touch()
            cut = root_path / "cut.mp4"
            cut.touch()

            with patch(
                "sanong_generation.composer.cut_video_by_audio_length",
                return_value=str(cut),
            ) as cutter:
                backend = DefaultMediaBackend(root_path, root_path, logs.append)
                selected = backend.material_for_segment([], set(), 0, 6.5)

        self.assertEqual(selected.material_id, 12)
        cutter.assert_called_once_with(str(source), 12, 6.5)
        self.assertTrue(any("本地三农素材" in message for message in logs))

    def test_audio_settings_preserve_existing_voice_mapping(self):
        settings = {
            "voice_set": {
                "api_type": 1,
                "role_0": 1,
                "spd_0": 5,
                "vol_0": 90,
                "role_1": 1,
                "spd_1": 5,
                "vol_1": 5,
                "pit_1": 5,
            }
        }
        audio = build_audio_settings(settings)
        self.assertEqual(audio["api_type"], 1)
        self.assertEqual(audio["audio_role"], 0)

    def test_legacy_edge_setting_is_forced_to_baidu_for_generation(self):
        settings = {
            "voice_set": {
                "api_type": 0,
                "role_0": 1,
                "spd_0": 5,
                "vol_0": 90,
                "role_1": 0,
                "spd_1": 5,
                "vol_1": 5,
                "pit_1": 5,
            }
        }
        audio = build_audio_settings(settings)
        self.assertEqual(audio["api_type"], 1)
        self.assertEqual(audio["audio_role"], 1)


class FakeMediaBackend:
    def prepare_segments(self, parts, audio_settings, settings, title, screen):
        return [
            PreparedSegment(Path(f"{index}.mp3"), Path(f"{index}.ass"), 8.0)
            for index, _part in enumerate(parts)
        ]

    def material_for_segment(self, tags, used_ids, screen, audio_length):
        material_id = len(used_ids) + 1
        return PreparedMaterial(material_id, Path(f"cut-{material_id}.mp4"))

    def render(self, segments, materials, intermediate_path, pic_time):
        intermediate_path.touch()
        return intermediate_path

    def add_music(self, intermediate_path, final_path):
        final_path.touch()
        return final_path


class SanongComposerTests(unittest.TestCase):
    def test_compose_returns_actual_video_without_end_video_dependency(self):
        settings = {
            "voice_set": {
                "api_type": 0,
                "role_0": 0,
                "spd_0": 0,
                "vol_0": 100,
            },
            "title_set": {},
            "srt_set": {},
            "end_video": {"end_video_path": "Z:/missing.mp4"},
        }
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            output_dir = root_path / "output"
            output_dir.mkdir()
            copy_file = write_excel_row(
                root_path / "copy.xlsx",
                ["测试标题", "三农", "片段1", "片段2", "片段3"],
            )
            label_file = write_excel_row(
                root_path / "label.xlsx", ["标签1", "标签2", "标签3"]
            )
            settings = {
                "voice_set": {
                    "api_type": 0,
                    "role_0": 0,
                    "spd_0": 0,
                    "vol_0": 100,
                },
                "title_set": {},
                "srt_set": {},
            }
            composer = SanongComposer(
                media=FakeMediaBackend(), log=lambda _message: None
            )
            results = composer.compose(
                copy_file, label_file, output_dir, "账号A", settings
            )

        self.assertEqual(results[0].video_path, output_dir / "测试标题.mp4")
        self.assertEqual(results[0].material_ids, (1, 2, 3))

    def test_compose_removes_title_scoped_audio_subtitle_and_cut_files(self):
        settings = {
            "voice_set": {
                "api_type": 0,
                "role_0": 0,
                "spd_0": 0,
                "vol_0": 100,
            },
            "title_set": {},
            "srt_set": {},
        }
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            output_dir = root_path / "output"
            output_dir.mkdir()
            copy_file = write_excel_row(
                root_path / "copy.xlsx",
                ["清理测试", "三农", "片段1", "片段2", "片段3"],
            )
            label_file = write_excel_row(
                root_path / "label.xlsx", ["标签1", "标签2", "标签3"]
            )

            class FileCreatingBackend(FakeMediaBackend):
                def prepare_segments(self, parts, audio_settings, settings, title, screen):
                    temp_dir = root_path / "tempConcateVideo" / "video_cache_file"
                    temp_dir.mkdir(parents=True)
                    segments = []
                    for index, _part in enumerate(parts):
                        audio = temp_dir / f"temp_final_audio{index}.mp3"
                        srt = temp_dir / f"temp_subtitle{index}.srt"
                        ass = temp_dir / f"temp_subtitle{index}.ass"
                        audio.touch()
                        srt.touch()
                        ass.touch()
                        segments.append(PreparedSegment(audio, ass, 8.0))
                    self.cut_files = []
                    for index in range(len(parts)):
                        cut = root_path / "cacheCutVideo" / f"cut_{index}.mp4"
                        cut.parent.mkdir(parents=True, exist_ok=True)
                        cut.touch()
                        self.cut_files.append(cut)
                    return segments

                def material_for_segment(self, tags, used_ids, screen, audio_length):
                    return PreparedMaterial(
                        len(used_ids) + 1,
                        self.cut_files[len(used_ids)],
                    )

            media = FileCreatingBackend()
            composer = SanongComposer(
                media=media,
                log=lambda _message: None,
                base_dir=root_path,
            )
            composer.compose(copy_file, label_file, output_dir, "账号A", settings)

            self.assertFalse(
                any((root_path / "tempConcateVideo").rglob("*"))
            )
            self.assertFalse(
                any((root_path / "cacheCutVideo").rglob("*"))
            )

    def test_permission_error_writing_video_index_does_not_fail_video(self):
        logs = []
        settings = {
            "voice_set": {
                "api_type": 0,
                "role_0": 0,
                "spd_0": 0,
                "vol_0": 100,
            },
            "title_set": {},
            "srt_set": {},
        }
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            output_dir = root_path / "output"
            output_dir.mkdir()
            copy_file = write_excel_row(
                root_path / "copy.xlsx",
                ["占用测试", "三农", "片段1", "片段2", "片段3"],
            )
            label_file = write_excel_row(
                root_path / "label.xlsx", ["标签1", "标签2", "标签3"]
            )
            composer = SanongComposer(
                media=FakeMediaBackend(), log=logs.append, base_dir=root_path
            )
            with patch(
                "sanong_generation.composer._append_xlsx",
                side_effect=PermissionError("文件被 WPS 占用"),
            ), patch("sanong_generation.composer.write_to_old_excel"):
                results = composer.compose(
                    copy_file, label_file, output_dir, "账号A", settings
                )
                self.assertEqual(len(results), 1)
                self.assertTrue(results[0].video_path.is_file())
                self.assertTrue(any("video_id.xlsx" in message for message in logs))


class SanongMetadataTests(unittest.TestCase):
    def test_append_xlsx_returns_fallback_when_target_is_locked(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "video_id.xlsx"
            with patch(
                "sanong_generation.composer.Workbook.save",
                side_effect=[PermissionError("locked"), None],
            ) as save:
                fallback = _append_xlsx(target, ["标题", "1.mp4"])

        self.assertNotEqual(fallback, target)
        self.assertIn("video_id_pending_", fallback.name)
        self.assertEqual(save.call_count, 2)


if __name__ == "__main__":
    unittest.main()
