# 合成文字图片介绍类视频

import asyncio
import os

from ffmpeg_tool.pic_trans_to_video import image_to_video
from ffmpeg_tool.subtitles_audio_tool import add_audio_and_subtitles_to_part, add_subtitles
from ffmpeg_tool.video_concat_tool import addCover, concatenate_videos_in_segments
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


# 添加音频字幕合成视频
async def addAss(ass_file, out_step1_path, out_step2_path):
    await add_subtitles(ass_file, out_step1_path, out_step2_path)

async def imgToVideo(pic_path, time, out_path):
    await image_to_video(pic_path, time, out_path)


class CompositeWordIntroVideo(QRunnable):
    def __init__(self, pic_path, title_ass_path, content_ass_path, output_final_path, show_time, first_page_complete_time=None):
        super().__init__()
        self.pic_path = pic_path
        self.title_ass_path = title_ass_path
        self.content_ass_path = content_ass_path
        self.output_final_path = output_final_path
        self.show_time = show_time
        self.first_page_complete_time = first_page_complete_time  # 第一页完整显示的时间点
        self.signals = WorkerSignals()

    def run(self):

        try:
            out_step1_path = 'step1.mp4'
            out_step2_path = 'step2.mp4'
            out_step3_path = 'step3.mp4'
            # out_step4_path = 'step4.mp4'
            if os.path.exists(out_step1_path):
                os.remove(out_step1_path)
            if os.path.exists(out_step2_path):
                os.remove(out_step2_path)
            # if os.path.exists(out_step3_path):
            #     os.remove(out_step3_path)
            # if os.path.exists(out_step4_path):
            #     os.remove(out_step4_path)
            # 1.将图片转为视频
            asyncio.run(imgToVideo(self.pic_path, self.show_time, out_step1_path))
            # 2.将两个字幕添加到视频
            asyncio.run(addAss(self.title_ass_path, out_step1_path, out_step2_path))

            asyncio.run(addAss(self.content_ass_path, out_step2_path, out_step3_path))

            asyncio.run(self.addCover(out_step3_path,  self.show_time))
            if os.path.exists(out_step1_path):
                os.remove(out_step1_path)
            if os.path.exists(out_step2_path):
                os.remove(out_step2_path)
            if os.path.exists(out_step3_path):
                os.remove(out_step3_path)
            # if os.path.exists(out_step4_path):
            #     os.remove(out_step4_path)
            self.signals.finished.emit('完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    # 添加封面
    async def addCover(self, video_path, pic_time):
        # 如果指定了第一页完整显示时间，则截取该时间点的画面作为封面
        if self.first_page_complete_time is not None and self.first_page_complete_time > 0:
            # 截取第一页完整显示后的画面（稍微延迟0.1秒确保所有字幕都出现）
            cover_time = self.first_page_complete_time + 0.1
        else:
            # 默认截取视频末尾的画面
            cover_time = pic_time - 0.1
        addCover(video_path, self.output_final_path, cover_time)

