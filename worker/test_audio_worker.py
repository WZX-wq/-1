import asyncio

from ffmpeg_tool.subtitles_audio_tool import generate_voice, bd_generate_voice
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


# 测试音频获取
class TestAudioWorker(QRunnable):
    def __init__(self, audio_setting):
        super().__init__()
        self.audio_setting = audio_setting
        self.signals = WorkerSignals()

    def run(self):
        try:
            asyncio.run(self.produce_process())
            self.signals.progressResultReady.emit(f'生成了试听音频')
            self.signals.testAudioResultReady.emit()
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    async def produce_process(self):
        if self.audio_setting['api_type'] == 1:
            # 调用 generate_voice 函数
            await generate_voice(
                one_text=self.audio_setting['test_text'],
                output_path="testoutput.mp3",
                increase_db=self.audio_setting['volume_value'],
                voice_name=self.audio_setting['audio_role'],
                speed=self.audio_setting['speed_value']
            )
        else:
            bd_generate_voice(
                text=self.audio_setting['test_text'],
                out_path="testoutput.mp3",
                role=self.audio_setting['audio_role'],
                spd=self.audio_setting['speed_value'],
                pit=self.audio_setting['tone_value'],
                vol=self.audio_setting['volume_value']
            )
