"""Render guide fixtures with real FFmpeg in an isolated working directory.

Database/AI responses are fixtures; page rendering, merging, music, watermark
and compression run through the production functions. No remote writes occur.
"""
import copy
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import main
from openpyxl import Workbook
from PIL import Image
from PyQt6.QtCore import QEventLoop, QThreadPool
from ai_tool.structured_content import normalize_guide_pages


class SmokeWindow(main.QObject):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)

    create_page_video = main.BatchAICutter.create_page_video
    on_success_occurred = main.BatchAICutter.on_success_occurred
    on_error_occurred = main.BatchAICutter.on_error_occurred


def verify(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    settings = json.loads((ROOT / 'setting.txt').read_text(encoding='utf-8'))
    os.environ['PATH'] = str(ROOT / 'ffmpeg-7.1.1-essentials_build' / 'bin') + os.pathsep + os.environ.get('PATH', '')
    app = main.QApplication.instance() or main.QApplication([])
    old_cwd = Path.cwd()
    original_material = destination / 'original.mp4'
    original_material.write_bytes(b'material must be preserved')

    def background(_video, image, **kwargs):
        Path(image).parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (1080, 1920), '#c3d4dc').save(image)
        return True

    cases = [
        ('itinerary', '古城一日游', [{'Day1·古城': {
            '行程安排': '上午参观古城 下午漫步街巷', '玩点亮点': '古城墙与青石小巷',
            '特色美食': '品尝当地烧饼', '注意事项': '穿舒适的鞋子'}}],
         main.BatchAICutter.compositeImageIntroVideo),
        ('food', '章丘美食攻略', [{'第1页·特色美食': {'项目1': {
            '名称': '【烧饼】', '简介/特色': '外酥里软 香气浓郁的当地美食', '价格信息': '10¥/份'}}}],
         main.BatchAICutter.compositeLocalStrategyVideo),
    ]
    try:
        os.chdir(destination)
        for folder in ('cacheMusic', 'cacheMusic2', 'tempConcateVideo/video_cache_file'):
            Path(folder).mkdir(parents=True, exist_ok=True)
        for folder in ('cacheMusic', 'cacheMusic2'):
            shutil.copy2(ROOT / 'blank.mp3', destination / folder / 'smoke_music.mp3')
        for kind, title, pages, compose in cases:
            copy_file = destination / f'{kind}_copy.xlsx'
            label_file = destination / f'{kind}_label.xlsx'
            # Round-trip the structured API result through the same JSON cells.
            pages = normalize_guide_pages(json.dumps(pages, ensure_ascii=False), kind)
            workbook = Workbook()
            workbook.active.append([title, '本地测试'] + [json.dumps(page, ensure_ascii=False) for page in pages])
            workbook.save(copy_file)
            workbook = Workbook()
            workbook.active.append(['章丘,美食'])
            workbook.save(label_file)
            output = destination / kind
            output.mkdir(exist_ok=True)
            window = SmokeWindow(
                randomVideoModelCheckBox=SimpleNamespace(isChecked=lambda: False),
                thread_pool=QThreadPool.globalInstance(), loop=QEventLoop(),
                error_flag=False, last_error_message='', _consecutive_system_failures=0,
                _stop_auto_generation=False, add_log=lambda message: print(message, flush=True),
                get_upload_accounts=lambda *_: [],
            )
            with patch.object(main, 'read_dict_from_txt', side_effect=lambda _: copy.deepcopy(settings)), \
                    patch.object(main, 'get_videos_by_keyword_1', return_value=[{'id': 1}]), \
                    patch.object(main, 'download_cn_video', return_value=str(original_material)), \
                    patch('ffmpeg_tool.video_concat_tool.extract_and_blur_random_frame', side_effect=background):
                compose(window, str(copy_file), str(label_file), str(output), '')
            video = output / (title + '.mp4')
            if not video.is_file() or not video.stat().st_size or window.error_flag:
                raise RuntimeError(f'{kind}: rendering failed: {window.last_error_message}')
            print(f'VERIFIED {kind}: {video} ({video.stat().st_size} bytes)', flush=True)
        if not original_material.is_file():
            raise RuntimeError('Source material was unexpectedly deleted')
    finally:
        os.chdir(old_cwd)


if __name__ == '__main__':
    verify(sys.argv[1])
