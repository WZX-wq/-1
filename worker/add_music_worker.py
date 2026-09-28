from sanong_generation.media_core import add_background_music
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable

class AddMusicWorker(QRunnable):
    def __init__(self, video_path, music_path, video_volume, music_volume, output_file):
        super().__init__()
        self.video_path = video_path
        self.music_path = music_path
        self.video_volume = video_volume
        self.music_volume = music_volume
        self.output_file = output_file
        self.signals = WorkerSignals()

    def run(self):
        try:
            add_background_music(
                self.video_path,
                self.music_path,
                self.video_volume,
                self.music_volume,
                self.output_file,
            )
            self.signals.finished.emit('添加背景音乐完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

