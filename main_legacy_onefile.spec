# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_submodules, copy_metadata


project_dir = os.path.abspath(SPECPATH)
legacy_pyqt_dir = os.path.join(project_dir, '.legacy-pyqt611')
source_deps_dir = os.path.join(project_dir, '.source-run-deps')
ffmpeg_bin_dir = os.path.join(project_dir, 'ffmpeg-7.1.1-essentials_build', 'bin')
legacy_qt_runtime_dir = os.path.join(project_dir, '.legacy-qt-runtime')
sys.path[:0] = [legacy_pyqt_dir, source_deps_dir]

package_metadata = (
    copy_metadata('imageio')
    + copy_metadata('imageio-ffmpeg')
    + copy_metadata('moviepy')
    + copy_metadata('openai-whisper')
)
hidden_imports = ['xlrd'] + collect_submodules('mysql.connector')


a = Analysis(
    ['main.py'],
    pathex=[legacy_pyqt_dir, source_deps_dir],
    binaries=[
        (os.path.join(ffmpeg_bin_dir, 'ffmpeg.exe'), 'ffmpeg-bin'),
        (os.path.join(ffmpeg_bin_dir, 'ffprobe.exe'), 'ffmpeg-bin'),
    ],
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

a.binaries = [
    item
    for item in a.binaries
    if 'imageio_ffmpeg\\binaries\\ffmpeg-' not in item[0].lower()
]

legacy_runtime_names = {
    'icu.dll', 'icuin.dll', 'icuuc.dll', 'icudt78.dll',
    'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
    'vcruntime140.dll', 'vcruntime140_1.dll',
}
a.binaries = [
    item for item in a.binaries
    if os.path.basename(item[0]).lower() not in legacy_runtime_names
]

# Keep the original PyQt6 wheel layout used by the known-good executable.
# PyInstaller 6.20 otherwise flattens Qt's runtime DLLs into the archive root;
# the older package kept them under PyQt6/Qt6/bin, which is also the path used
# by the PyQt6 runtime loader on the target Server 2016 machine.
qt_bin_names = {
    'qt6core.dll', 'qt6gui.dll', 'qt6multimedia.dll',
    'qt6multimediawidgets.dll', 'qt6network.dll', 'qt6pdf.dll',
    'qt6svg.dll', 'qt6widgets.dll', 'icu.dll', 'icuin.dll', 'icuuc.dll',
    'opengl32sw.dll', 'avcodec-61.dll', 'avformat-61.dll', 'avutil-59.dll',
    'swresample-5.dll', 'swscale-8.dll', 'msvcp140.dll', 'msvcp140_1.dll',
    'msvcp140_2.dll', 'vcruntime140.dll', 'vcruntime140_1.dll',
}
a.binaries = [
    (
        os.path.join('PyQt6', 'Qt6', 'bin', os.path.basename(dest))
        if os.path.basename(dest).lower() in qt_bin_names
        and os.path.normcase(source).startswith(os.path.normcase(os.path.join(legacy_pyqt_dir, 'PyQt6', 'Qt6', 'bin')))
        else dest,
        source,
        kind,
    )
    for dest, source, kind in a.binaries
]

for runtime_name in sorted(legacy_runtime_names - {'icudt78.dll'}):
    a.binaries.append(
        (
            os.path.join('PyQt6', 'Qt6', 'bin', runtime_name),
            os.path.join(legacy_qt_runtime_dir, runtime_name),
            'BINARY',
        )
    )

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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['tb.ico'],
)
