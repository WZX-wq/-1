# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_submodules, copy_metadata


msvc_runtime_dir = (
    r'C:\Windows\System32'
)
windows_icu_dir = r'C:\Windows\System32'
qt_runtime_dlls = [
    'concrt140.dll',
    'msvcp140.dll',
    'msvcp140_1.dll',
    'msvcp140_2.dll',
    'msvcp140_atomic_wait.dll',
    'msvcp140_codecvt_ids.dll',
    'ucrtbase.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'vcruntime140_threads.dll',
]
qt_icu_dlls = [
    (os.path.join(windows_icu_dir, name), 'PyQt6/Qt6/bin')
    for name in ('icu.dll', 'icuuc.dll', 'icuin.dll')
]
qt_icu_sources = {
    os.path.normcase(os.path.abspath(source))
    for source, _ in qt_icu_dlls
}
ffmpeg_bin_dir = os.path.join(os.getcwd(), 'ffmpeg-7.1.1-essentials_build', 'bin')
package_metadata = (
    copy_metadata('imageio')
    + copy_metadata('imageio-ffmpeg')
    + copy_metadata('moviepy')
    + copy_metadata('openai-whisper')
)
hidden_imports = ['xlrd'] + collect_submodules('mysql.connector')


a = Analysis(
    ['main.py'],
    pathex=['.source-run-deps'],
    # Qt6Core uses the bundled ICU 78 build, so keep the extraction-root MSVC
    # runtime version-consistent with that ICU build (and backward-compatible
    # with PyQt6) instead of mixing runtime versions from different packages.
    binaries=(
        [(os.path.join(msvc_runtime_dir, name), '.') for name in qt_runtime_dlls]
        + qt_icu_dlls
        + [(os.path.join(ffmpeg_bin_dir, 'ffmpeg.exe'), 'ffmpeg-bin')]
        + [(os.path.join(ffmpeg_bin_dir, 'ffprobe.exe'), 'ffmpeg-bin')]
    ),
    datas=package_metadata + [
        ('setting.txt', '.'),
        ('tb.ico', '.'),
        ('video_ai_config.example.json', '.'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torchaudio',
        'torchvision',
        'transformers',
        'sentence_transformers',
        'spacy',
        'thinc',
        'sklearn',
        'tensorflow',
        'librosa',
        # ffmpeg-python only uses past.builtins; these unused compatibility
        # namespaces probe top-level modules and collide with local test.py.
        'future.moves',
        'future.backports',
        'future.tests',
        'libfuturize',
        'libpasteurize',
        'matplotlib',
        'tkinter',
        '_tkinter',
    ],
    noarchive=False,
    optimize=0,
)

# PyInstaller can discover Poppler's private ICU through the host PATH. Qt6
# expects the Windows ICU forwarding DLLs, so exclude Poppler's incompatible
# copies from every destination.
a.binaries = [
    item for item in a.binaries
    if (
        os.path.basename(item[0]).lower() not in {'icu.dll', 'icuuc.dll', 'icuin.dll', 'icudt78.dll'}
        or os.path.normcase(os.path.abspath(item[1])) in qt_icu_sources
    )
    and 'imageio_ffmpeg\\binaries\\ffmpeg-' not in item[0].lower()
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    # One-file extraction stays beside the launched program instead of using C:\Users\...\Temp.
    runtime_tmpdir='.runtime_tmp',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['tb.ico'],
)
