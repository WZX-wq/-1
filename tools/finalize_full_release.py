"""Restore the portable full-version layout after PyInstaller COLLECT."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ASSETS = (
    'tb.ico', 'soft_pic', 'endCredits', 'gifMaterial', 'strategy_pic',
    'video_model_set', 'cacheMusic', 'cacheMusic1', 'cacheMusic2', 'cacheMusic3',
    'img.jpg', 'blank.ass', 'blank.mp3', 'version.json', 'white.png', 'xq.png',
    'video_ai_config.example.json', 'setting.txt',
)
WORKSPACES = (
    'cacheVideo', 'cacheAFRVideo', 'cacheCNVideo', 'cacheCoverVideo', 'cacheCutVideo',
    'notSuccess', 'output', 'tempConcateVideo', 'temp_title', 'syncVideo',
    'person_images', 'pic_infor_model', 'pic_infor_model2', 'coverPicMaterial',
)


def finalize(release: Path, *, private: bool = False):
    release = release.resolve()
    internal = release / '_internal'
    if not (release / 'main.exe').is_file() or not internal.is_dir():
        raise RuntimeError('Expected a complete full-version PyInstaller release directory.')
    for name in ASSETS:
        source = internal / name
        target = release / name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        elif source.is_file():
            shutil.copy2(source, target)
        elif name == 'cacheMusic3':
            # PyInstaller omits empty input directories; this writable pool is
            # still part of a fresh full-version installation.
            target.mkdir(exist_ok=True)
        else:
            raise RuntimeError(f'Missing bundled resource: {name}')
    for name in WORKSPACES:
        (release / name).mkdir(exist_ok=True)
    if private:
        from PyInstaller.archive.readers import CArchiveReader
        archive = CArchiveReader(str(release / 'main.exe'))
        pyz = archive.open_embedded_archive(next(name for name in archive.toc if name.lower().endswith('.pyz')))
        if 'video_ai_embedded_config' not in pyz.toc:
            raise RuntimeError('Private release does not contain embedded AI defaults.')
        shutil.copy2(Path(__file__).with_name('PRIVATE_RELEASE_README.txt'), release / '使用说明.txt')
    # Preserve both modern nested Qt layout and older Windows flat fallback.
    qt_bin = internal / 'PyQt6' / 'Qt6' / 'bin'
    for source in qt_bin.glob('*.dll'):
        shutil.copy2(source, internal / source.name)
    for name in ('Qt6Core.dll', 'Qt6Widgets.dll', 'icu.dll', 'icuuc.dll', 'icuin.dll',
                 'msvcp140.dll', 'vcruntime140.dll'):
        if not (internal / name).is_file():
            raise RuntimeError(f'Missing compatible runtime: {name}')
    print(f'Full-version portable release ready: {release}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release', type=Path)
    parser.add_argument('--private', action='store_true', help='Validate embedded defaults and include private usage notes')
    args = parser.parse_args()
    finalize(args.release, private=args.private)
