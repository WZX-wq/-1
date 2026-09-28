import asyncio

from ffmpeg_tool.add_watermark_tool import add_text_watermark, add_pic_watermark
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
                asyncio.run(self.add_pic_watermark())
            self.signals.finished.emit('添加视频水印完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    # 文字水印
    async def add_text_watermark(self):
        add_text_watermark(self.video_path, self.output_file, self.watermark_setting)

    # 图片水印
    async def add_pic_watermark(self):
        add_pic_watermark(self.video_path, self.pic_path, self.output_file, self.watermark_setting)