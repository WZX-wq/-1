# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_submodules, copy_metadata


project_dir = os.path.abspath(SPECPATH)
legacy_pyqt_dir = os.environ.get(
    'LEGACY_PYQT_DIR',
    os.path.join(project_dir, '.legacy-pyqt67'),
)
source_deps_dir = os.path.join(project_dir, '.source-run-deps')
ffmpeg_bin_dir = os.path.join(project_dir, 'ffmpeg-7.1.1-essentials_build', 'bin')
legacy_icu_dir = os.path.join(project_dir, '.legacy-server2016-runtime')
legacy_icu_names = {'icu.dll', 'icuuc.dll', 'icuin.dll'}
legacy_qt_ffmpeg_dir = os.path.join(
    project_dir, '.legacy-pyqt611', 'PyQt6', 'Qt6', 'bin'
)
legacy_qt_runtime_dir = os.path.join(project_dir, '.legacy-qt-runtime')
legacy_runtime_names = {
    'icu.dll', 'icuin.dll', 'icuuc.dll', 'icudt78.dll',
    'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
    'vcruntime140.dll', 'vcruntime140_1.dll',
}

# Spec-time helpers such as copy_metadata() and collect_submodules() use the
# interpreter search path rather than Analysis.pathex.
sys.path[:0] = [legacy_pyqt_dir, source_deps_dir]

package_metadata = (
    copy_metadata('imageio')
    + copy_metadata('imageio-ffmpeg')
    + copy_metadata('moviepy')
    + copy_metadata('openai-whisper')
)
hidden_imports = ['xlrd'] + collect_submodules('mysql.connector')
runtime_data = [
    ('tb.ico', '.'),
    ('video_ai_config.example.json', '.'),
    # UI and template assets used through paths relative to the executable.
    ('soft_pic', 'soft_pic'),
    ('endCredits', 'endCredits'),
    ('gifMaterial', 'gifMaterial'),
    ('strategy_pic', 'strategy_pic'),
    ('video_model_set', 'video_model_set'),
    ('img.jpg', '.'),
    ('blank.ass', '.'),
    ('blank.mp3', '.'),
    ('version.json', '.'),
    ('white.png', '.'),
    ('xq.png', '.'),
    # Default music pools are part of the application's normal workflow.
    ('cacheMusic', 'cacheMusic'),
    ('cacheMusic1', 'cacheMusic1'),
    ('cacheMusic2', 'cacheMusic2'),
    ('cacheMusic3', 'cacheMusic3'),
]


a = Analysis(
    ['main.py'],
    pathex=[legacy_pyqt_dir, source_deps_dir],
    binaries=[
        *[
            (os.path.join(legacy_icu_dir, name), 'PyQt6/Qt6/bin')
            for name in sorted(legacy_icu_names)
        ],
        (os.path.join(ffmpeg_bin_dir, 'ffmpeg.exe'), 'ffmpeg-bin'),
        (os.path.join(ffmpeg_bin_dir, 'ffprobe.exe'), 'ffmpeg-bin'),
    ],
    datas=package_metadata + [('setting.txt', '.')] + runtime_data,
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

# Avoid the imageio-ffmpeg fallback binary; the package uses the pinned FFmpeg
# build above, matching the original application's runtime layout.
a.binaries = [
    item
    for item in a.binaries
    if (
        'imageio_ffmpeg\\binaries\\ffmpeg-' not in item[0].lower()
        and (
            os.path.basename(item[0]).lower() not in legacy_runtime_names
            or os.path.dirname(os.path.abspath(item[1])) == legacy_icu_dir
        )
    )
]

# Preserve the complete PyQt6 wheel layout.  Do this by source directory rather
# than by a fixed DLL-name list: Qt 6.7 and Qt 6.11 ship different multimedia
# and runtime DLL names.  The nested layout is important because the Qt loader
# searches PyQt6/Qt6/bin relative to the Qt Python bindings.
qt_bin_root = os.path.normcase(
    os.path.abspath(os.path.join(legacy_pyqt_dir, 'PyQt6', 'Qt6', 'bin'))
) + os.sep
a.binaries = [
    (
        os.path.join('PyQt6', 'Qt6', 'bin', os.path.basename(dest))
        if os.path.normcase(os.path.abspath(source)).startswith(qt_bin_root)
        else dest,
        source,
        kind,
    )
    for dest, source, kind in a.binaries
]

for runtime_name in sorted(legacy_runtime_names - {'icudt78.dll'} - legacy_icu_names):
    # Prefer the CRT shipped with the selected Qt wheel.  The fallback keeps
    # the build reproducible if a wheel omits one of the split CRT files.
    runtime_source = os.path.join(
        legacy_pyqt_dir, 'PyQt6', 'Qt6', 'bin', runtime_name
    )
    if not os.path.isfile(runtime_source):
        runtime_source = os.path.join(legacy_qt_runtime_dir, runtime_name)
    if not os.path.isfile(runtime_source):
        continue
    a.binaries.append(
        (
            os.path.join('PyQt6', 'Qt6', 'bin', runtime_name),
            runtime_source,
            'BINARY',
        )
    )

# PyQt6's Qt Multimedia plugin loads these FFmpeg DLLs by name at runtime, but
# the Qt 6.7 wheel does not ship the codec binaries.  Reuse the matching
# avcodec-61/avformat-61 family already present in the bundled Qt runtime.
for runtime_name in sorted(os.listdir(legacy_qt_ffmpeg_dir)):
    lower_name = runtime_name.lower()
    if not (
        lower_name.endswith('.dll')
        and lower_name.startswith(('avcodec-', 'avformat-', 'avutil-', 'swresample-', 'swscale-'))
    ):
        continue
    runtime_source = os.path.join(legacy_qt_ffmpeg_dir, runtime_name)
    if os.path.isfile(runtime_source):
        a.binaries.append(
            (
                os.path.join('PyQt6', 'Qt6', 'bin', runtime_name),
                runtime_source,
                'BINARY',
            )
        )

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['tb.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='main',
)
