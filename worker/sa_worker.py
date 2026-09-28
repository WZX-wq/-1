import asyncio
import os

from ffmpeg_tool.subtitles_audio_tool import AB_produce_audio_and_subtitles_to_path
from sanong_generation.media_core import generate_audio_subtitles
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


# 音频字幕生成
class SaWorker(QRunnable):
    def __init__(self, ai_text, audio_setting):
        super().__init__()
        self.ai_text = ai_text
        self.audio_setting = audio_setting
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 获取当前时间戳
            # timestamp = int(time.time())
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            # 判断且创建临时文件夹
            if not os.path.exists(tamp_folder_path):
                os.makedirs(tamp_folder_path)
            video_tamp_path_name = 'video' + f'_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)
            if not os.path.exists(video_tamp_path):
                os.makedirs(video_tamp_path)
            generate_audio_subtitles(
                self.ai_text,
                self.audio_setting,
                video_tamp_path,
                self.signals.progressResultReady.emit,
            )

            # temp_infor = {'num': len(self.ai_text), 'path': video_tamp_path}
            #
            # # 返回临时文件信息
            self.signals.finished.emit('完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

# 音频字幕生成
class SaDHWorker(QRunnable):
    def __init__(self, ai_text, audio_setting):
        super().__init__()
        self.ai_text = ai_text
        self.audio_setting = audio_setting
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 获取当前时间戳
            # timestamp = int(time.time())
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            # 判断且创建临时文件夹
            if not os.path.exists(tamp_folder_path):
                os.makedirs(tamp_folder_path)
            video_tamp_path_name = 'video' + f'_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)
            if not os.path.exists(video_tamp_path):
                os.makedirs(video_tamp_path)
            for i, text in enumerate(self.ai_text):
                asyncio.run(self.produce_process(self.audio_setting['api_type'], video_tamp_path, text, i))
                self.signals.progressResultReady.emit(f'正在处理文案中，目前已经处理了{i + 1}片段，生成了音频字幕')

            # temp_infor = {'num': len(self.ai_text), 'path': video_tamp_path}
            #
            # # 返回临时文件信息
            self.signals.finished.emit('完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    async def produce_process(self, api_type, video_tamp_path, text, i):
        await AB_produce_audio_and_subtitles_to_path(api_type, video_tamp_path, text, i, self.audio_setting)
        print('完成一个片段')
