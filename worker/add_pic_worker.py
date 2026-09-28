import asyncio
import os

from ffmpeg_tool.add_music_tool import add_bgm_to_video
from ffmpeg_tool.add_watermark_tool import add_watermark, add_image_to_video
from ffmpeg_tool.video_concat_tool import create_video_with_image_start, extract_specific_frame
from worker.composite_word_intro_video_worker import addAss
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable

# 视频封面
class AddPicWorker(QRunnable):
    def __init__(self, video_path, pic_title_video, pic_material_file, ass_file, output_file):
        super().__init__()
        self.video_path = video_path
        self.pic_title_video = pic_title_video
        self.pic_material_file = pic_material_file
        self.ass_file = ass_file
        self.output_file = output_file
        self.signals = WorkerSignals()

    def run(self):
        try:
            asyncio.run(self.process_files())
            self.signals.finished.emit('添加封面完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    async def process_files(self):

        temp_output_pic_file = 'cover_pic.mp4'
        temp_output_file = 'cover.mp4'

        position = (0, 600)  # 图片位置 (x, y)
        size = (1080, 400)  # 图片大小 (width, height)
        opacity = 0.4  # 图片透明度
        duration = (0, 10)  # 图片显示时间 (start_time, end_time)

        if os.path.exists(temp_output_pic_file):
            os.remove(temp_output_pic_file)
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)

        # 添加透明图片
        # add_image_to_video(self.pic_title_video, temp_output_pic_file, self.pic_material_file, position, size, opacity, duration)

        # # 添加标题
        # await addAss(self.ass_file, temp_output_pic_file, temp_output_file)

        await addAss(self.ass_file, self.pic_title_video, temp_output_file)

        output_image_path = 'cover.jpg'
        if os.path.exists(output_image_path):
            os.remove(output_image_path)
        extract_specific_frame(temp_output_file, output_image_path, 0.2)
        create_video_with_image_start(self.video_path, output_image_path, self.output_file)




