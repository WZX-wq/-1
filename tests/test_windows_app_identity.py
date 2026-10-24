import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import windows_app_identity as identity


class WindowsAppIdentityTests(unittest.TestCase):
    def setUp(self):
        identity._ICON_HANDLES.clear()
        self.addCleanup(identity._ICON_HANDLES.clear)
        platform = patch.object(sys, 'platform', 'win32')
        platform.start()
        self.addCleanup(platform.stop)

    def test_explicit_full_version_app_id_is_set(self):
        function = Mock(return_value=0)
        with patch.object(identity, '_library', return_value=SimpleNamespace(
                SetCurrentProcessExplicitAppUserModelID=function)):
            self.assertTrue(identity.set_process_app_id())
        function.assert_called_once_with('KunQiong.VideoStudio.Full')

    def test_large_and_small_native_icons_have_pointer_sized_handles_and_stay_alive(self):
        user32 = SimpleNamespace(LoadImageW=Mock(side_effect=[0x100000001, 0x100000002]),
                                 SendMessageW=Mock(return_value=0),
                                 GetSystemMetrics=Mock(side_effect=lambda item: 32 if item in (11, 12) else 16))
        with patch.object(identity, '_library', return_value=user32):
            self.assertTrue(identity.apply_native_window_icon(123, Path('tb.ico')))
            self.assertTrue(identity.apply_native_window_icon(123, Path('tb.ico')))
        self.assertEqual(user32.LoadImageW.call_count, 2)
        calls = user32.SendMessageW.call_args_list
        self.assertEqual(calls[0].args, (123, identity.WM_SETICON, 1, 0x100000001))
        self.assertEqual(calls[1].args, (123, identity.WM_SETICON, 0, 0x100000002))
        self.assertEqual(len(identity._ICON_HANDLES), 2)

    def test_icon_failure_does_not_prevent_the_application_opening(self):
        with patch.object(identity, '_library', side_effect=OSError('unavailable')):
            self.assertFalse(identity.set_process_app_id())
            self.assertFalse(identity.apply_native_window_icon(123, Path('tb.ico')))

    def test_other_platforms_skip_windows_apis(self):
        with patch.object(sys, 'platform', 'linux'), patch.object(identity, '_library') as library:
            self.assertFalse(identity.set_process_app_id())
            self.assertFalse(identity.apply_native_window_icon(123, Path('tb.ico')))
            library.assert_not_called()


if __name__ == '__main__':
    unittest.main()
