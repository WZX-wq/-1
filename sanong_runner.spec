# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_submodules


project_dir = os.path.abspath(SPECPATH)
legacy_pyqt_dir = os.path.join(project_dir, ".legacy-pyqt67")
source_deps_dir = os.path.join(project_dir, ".source-run-deps")
python_dir = os.path.join(project_dir, ".build-python312-official")
ffmpeg_dir = os.path.join(project_dir, "ffmpeg-7.1.1-essentials_build", "bin")
system_dir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
legacy_icu_dir = os.path.join(project_dir, ".legacy-server2016-runtime")
legacy_qt_runtime_dir = os.path.join(project_dir, ".legacy-qt-runtime")
legacy_icu_names = {"icu.dll", "icuin.dll", "icuuc.dll"}
legacy_qt_runtime_names = {
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
}

sys.path[:0] = [legacy_pyqt_dir, source_deps_dir, project_dir]

runtime_binaries = [
    *[
        (os.path.join(legacy_icu_dir, name), "PyQt6/Qt6/bin")
        for name in sorted(legacy_icu_names)
    ],
    (os.path.join(python_dir, "vcruntime140.dll"), "."),
    (os.path.join(python_dir, "vcruntime140_1.dll"), "."),
    (os.path.join(system_dir, "msvcp140.dll"), "."),
    (os.path.join(system_dir, "ucrtbase.dll"), "."),
    (os.path.join(ffmpeg_dir, "ffmpeg.exe"), "ffmpeg-bin"),
    (os.path.join(ffmpeg_dir, "ffprobe.exe"), "ffmpeg-bin"),
]

hidden_imports = (
    ["xlrd", "xlwt"]
    + collect_submodules("mysql.connector")
)

a = Analysis(
    ["sanong_gui.py"],
    pathex=[legacy_pyqt_dir, source_deps_dir, project_dir],
    binaries=runtime_binaries,
    # Keep a read-only fallback copy inside _internal. The release root still
    # receives the mutable soft_pic directory, but the GUI can render its logo
    # even when a user launches from a copied executable without that folder.
    datas=[(os.path.join(project_dir, "soft_pic"), "soft_pic")],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PySide6",
        "PySide2",
        "whisper",
        "torch",
        "torchaudio",
        "torchvision",
        "transformers",
        "sentence_transformers",
        "tensorflow",
        "spacy",
        "thinc",
        "sklearn",
        "librosa",
        "pandas",
        "scipy",
        "numba",
        "llvmlite",
        "moviepy",
        "imageio",
        "imageio_ffmpeg",
        "matplotlib",
        "tkinter",
        "_tkinter",
        "future.moves",
        "future.backports",
        "future.tests",
        "libfuturize",
        "libpasteurize",
    ],
    noarchive=False,
    optimize=0,
)

# The pinned FFmpeg binaries above are the only copy used. ICU must come from
# the Server 2016 forwarding runtime rather than the build machine.
a.binaries = [
    item
    for item in a.binaries
    if "imageio_ffmpeg\\binaries\\ffmpeg-" not in item[1].lower()
    and (
        not os.path.basename(item[0]).lower().startswith("icu")
        or os.path.normcase(item[1]).startswith(os.path.normcase(legacy_icu_dir))
    )
]

# Preserve the PyQt wheel layout so Qt can resolve its adjacent DLLs even on
# machines with restricted PATH-based lookup.
qt_bin_names = {
    "qt6core.dll",
    "qt6gui.dll",
    "qt6widgets.dll",
    "icu.dll",
    "icuin.dll",
    "icuuc.dll",
    "opengl32sw.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
}
a.binaries = [
    (
        os.path.join("PyQt6", "Qt6", "bin", os.path.basename(dest))
        if os.path.basename(dest).lower() in qt_bin_names
        and os.path.normcase(source).startswith(
            os.path.normcase(os.path.join(legacy_pyqt_dir, "PyQt6", "Qt6", "bin"))
        )
        else dest,
        source,
        kind,
    )
    for dest, source, kind in a.binaries
]

for runtime_name in sorted(legacy_qt_runtime_names):
    runtime_source = os.path.join(
        legacy_pyqt_dir, "PyQt6", "Qt6", "bin", runtime_name
    )
    if not os.path.isfile(runtime_source):
        runtime_source = os.path.join(legacy_qt_runtime_dir, runtime_name)
    if not os.path.isfile(runtime_source):
        continue
    a.binaries.append(
        (
            os.path.join("PyQt6", "Qt6", "bin", runtime_name),
            runtime_source,
            "BINARY",
        )
    )

# Keep flat copies for Windows Server systems whose loader does not resolve
# Qt's adjacent bin directory reliably from extension modules.
for qt_name in ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"):
    a.binaries.append(
        (
            qt_name,
            os.path.join(legacy_pyqt_dir, "PyQt6", "Qt6", "bin", qt_name),
            "BINARY",
        )
    )

for icu_name in sorted(legacy_icu_names):
    a.binaries.append(
        (
            icu_name,
            os.path.join(legacy_icu_dir, icu_name),
            "BINARY",
        )
    )

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="三农视频生成",
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
    icon=["tb.ico"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="三农视频生成",
)
