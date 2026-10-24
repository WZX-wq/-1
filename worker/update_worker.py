"""Background update checks used by the GUI startup path."""

from PyQt6.QtCore import QRunnable

from worker.worker_signals import WorkerSignals


class UpdateCheckWorker(QRunnable):
    """Run network update checks without blocking Qt's GUI thread."""

    def __init__(self, checker):
        super().__init__()
        self.checker = checker
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.updateResultReady.emit(self.checker.check_for_updates())
        except Exception as error:
            self.signals.errorOccurred.emit(str(error))
