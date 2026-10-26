import asyncio

from edge_tts import list_voices
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class VoiceListSignals(QObject):
    finished = pyqtSignal(object)
    errorOccurred = pyqtSignal(str)


class EdgeVoiceListWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = VoiceListSignals()

    def run(self):
        try:
            self.signals.finished.emit(asyncio.run(list_voices()))
        except Exception as error:
            self.signals.errorOccurred.emit(str(error))
