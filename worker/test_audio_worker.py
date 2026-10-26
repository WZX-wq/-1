import asyncio

from ffmpeg_tool.subtitles_audio_tool import choose_random_audio_voice, synthesize_provider_voice
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


# 测试音频获取
class TestAudioWorker(QRunnable):
    def __init__(self, audio_setting):
        super().__init__()
        self.audio_setting = choose_random_audio_voice(audio_setting)
        self.signals = WorkerSignals()

    def run(self):
        try:
            asyncio.run(self.produce_process())
            self.signals.progressResultReady.emit(f'生成了试听音频')
            self.signals.testAudioResultReady.emit()
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    async def produce_process(self):
        await synthesize_provider_voice(
            self.audio_setting,
            self.audio_setting['test_text'],
            "testoutput.mp3",
        )
