import asyncio
import shutil
from pathlib import Path

from ffmpeg_tool.add_watermark_tool import add_text_watermark, add_pic_watermark, resolve_watermark_path
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


# 添加水印
class AddWatermarkWorker(QRunnable):
    def __init__(self, video_path, output_file, watermark_setting, watermark_type=1, pic_path=None):
        super().__init__()
        self.video_path = video_path
        self.pic_path = pic_path
        self.output_file = output_file
        self.watermark_type = watermark_type
        self.watermark_setting = watermark_setting
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.watermark_type == 1:
                asyncio.run(self.add_text_watermark())
            else:
                resolved_pic = resolve_watermark_path(self.pic_path)
                if not resolved_pic:
                    source = Path(self.video_path)
                    output = Path(self.output_file)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    if source.resolve() != output.resolve():
                        shutil.copy2(source, output)
                    if not output.is_file() or output.stat().st_size == 0:
                        raise RuntimeError('跳过水印后视频文件未成功保存')
                    self.signals.finished.emit(
                        f'跳过水印：图片未设置或已失效（{self.pic_path or "未设置"}），视频已保留；需要水印时请重新选择图片'
                    )
                    return
                self.pic_path = resolved_pic
                asyncio.run(self.add_pic_watermark())
            output = Path(self.output_file)
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError('水印处理未生成有效视频文件')
            self.signals.finished.emit('添加视频水印完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    # 文字水印
    async def add_text_watermark(self):
        add_text_watermark(self.video_path, self.output_file, self.watermark_setting)

    # 图片水印
    async def add_pic_watermark(self):
        add_pic_watermark(self.video_path, self.pic_path, self.output_file, self.watermark_setting)
