import sys
import tempfile
import marshal
import os
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class EndVideoPortabilityTests(unittest.TestCase):
    def test_stale_absolute_path_falls_back_to_bundled_end_credit(self):
        import main

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'endCredits').mkdir()
            bundled = root / 'endCredits' / 'portable_end.mp4'
            bundled.write_bytes(b'path-resolution fixture')
            window = SimpleNamespace(all_setting_dict={
                'end_video': {'end_video_path': r'D:\old-computer\AI游江西.mp4'}
            })
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, 'executable', str(root / 'main.exe')), \
                    patch.object(sys, '_MEIPASS', '', create=True):
                resolved = main.BatchAICutter._resolve_end_video_path(window)

        self.assertEqual(Path(resolved), bundled.resolve())
        self.assertEqual(
            Path(window.all_setting_dict['end_video']['end_video_path']),
            bundled.resolve(),
        )

    def test_existing_custom_path_still_wins(self):
        import main

        with tempfile.TemporaryDirectory() as temp_dir:
            custom = Path(temp_dir) / 'custom_end.mp4'
            custom.write_bytes(b'custom')
            window = SimpleNamespace(all_setting_dict={
                'end_video': {'end_video_path': str(custom)}
            })
            resolved = main.BatchAICutter._resolve_end_video_path(window)

        self.assertEqual(resolved, str(custom))


@unittest.skipUnless(os.environ.get('PACKAGED_EXE_PATH'), 'Set PACKAGED_EXE_PATH to validate the full-version EXE')
class PackagedEndVideoPortabilityTests(EndVideoPortabilityTests):
    @classmethod
    def setUpClass(cls):
        from PyInstaller.archive.readers import CArchiveReader
        import main as source_main

        archive = CArchiveReader(os.environ['PACKAGED_EXE_PATH'])
        main_code = marshal.loads(archive.extract('main'))
        cutter_code = next(
            code for code in main_code.co_consts
            if isinstance(code, types.CodeType) and code.co_name == 'BatchAICutter'
        )
        method_code = next(
            code for code in cutter_code.co_consts
            if isinstance(code, types.CodeType) and code.co_name == '_resolve_end_video_path'
        )
        cls.resolve_end_video_path = staticmethod(
            types.FunctionType(method_code, source_main.__dict__)
        )

    def test_stale_absolute_path_falls_back_to_bundled_end_credit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'endCredits').mkdir()
            bundled = root / 'endCredits' / 'portable_end.mp4'
            bundled.write_bytes(b'path-resolution fixture')
            window = SimpleNamespace(all_setting_dict={
                'end_video': {'end_video_path': r'D:\old-computer\AI游江西.mp4'}
            })
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, 'executable', str(root / 'main.exe')), \
                    patch.object(sys, '_MEIPASS', '', create=True):
                resolved = self.resolve_end_video_path(window)

        self.assertEqual(Path(resolved), bundled.resolve())

    def test_returns_none_when_neither_configured_nor_bundled_end_video_exists(self):
        import main

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            window = SimpleNamespace(all_setting_dict={'end_video': {}})
            with patch.object(sys, 'frozen', True, create=True), \
                    patch.object(sys, 'executable', str(root / 'main.exe')), \
                    patch.object(sys, '_MEIPASS', '', create=True), \
                    patch.object(main, '__file__', str(root / 'main.py')), \
                    patch.object(Path, 'cwd', return_value=root):
                self.assertIsNone(main.BatchAICutter._resolve_end_video_path(window))


if __name__ == '__main__':
    unittest.main()
