"""Bind the full-version brand to Windows taskbar identity and native icons."""
from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from pathlib import Path


APP_USER_MODEL_ID = 'KunQiong.VideoStudio.Full'
WM_SETICON = 0x0080
WM_GETICON = 0x007F
_ICON_HANDLES: dict[tuple[str, int, int], int] = {}


def _library(name):
    return ctypes.WinDLL(name, use_last_error=True)


def set_process_app_id() -> bool:
    """Call before QApplication/window creation so main.exe is not misgrouped."""
    if sys.platform != 'win32':
        return False
    try:
        function = _library('shell32').SetCurrentProcessExplicitAppUserModelID
        function.argtypes = [wintypes.LPCWSTR]
        function.restype = ctypes.c_long
        if function(APP_USER_MODEL_ID) < 0:
            raise OSError('Windows rejected the application taskbar identity')
        return True
    except (OSError, AttributeError) as error:
        logging.warning('Windows taskbar identity could not be set: %s', error)
        return False


def apply_native_window_icon(window_id: int, icon_path: Path) -> bool:
    """Apply both icons after Qt has created the final frameless HWND.

    Windows retains the HICON rather than copying it. Keep handles alive for
    the process lifetime; clearing them early restores the generic taskbar icon.
    """
    if sys.platform != 'win32':
        return False
    try:
        user32 = _library('user32')
        load = user32.LoadImageW
        load.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                         ctypes.c_int, ctypes.c_int, wintypes.UINT]
        load.restype = wintypes.HANDLE
        send = user32.SendMessageW
        send.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        send.restype = wintypes.LPARAM
        metrics = user32.GetSystemMetrics
        metrics.argtypes = [ctypes.c_int]
        metrics.restype = ctypes.c_int
        path = str(Path(icon_path).resolve())
        for icon_type, width_metric, height_metric in ((1, 11, 12), (0, 49, 50)):
            width, height = metrics(width_metric), metrics(height_metric)
            identity = (path, width, height)
            handle = _ICON_HANDLES.get(identity)
            if not handle:
                handle = load(None, path, 1, width, height, 0x0010)  # IMAGE_ICON, LR_LOADFROMFILE
                if not handle:
                    raise OSError('Windows could not load the branded icon')
                _ICON_HANDLES[identity] = handle
            send(window_id, WM_SETICON, icon_type, handle)
        return True
    except (OSError, AttributeError, ValueError) as error:
        logging.warning('Windows native window icons could not be set: %s', error)
        return False
