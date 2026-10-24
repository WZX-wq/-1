"""Exercise the full-version entry points with real Qt custom-button dialogs.

Load only the relevant methods to avoid opening the application or contacting
external services. When PACKAGED_EXE_PATH is set, repeat against shipped code.
"""
import ast
import marshal
import os
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget,
)


METHODS = ('aiDisposeTitle', 'compositeVideo', 'video_model_delete')
WORKERS = (
    'AiDisposeIntroTitle', 'AiDisposeMsIntroTitle', 'AiDisposeStrategyTitle',
    'AiDisposeCNIntroTitle', 'AiDisposeWordIntroTitle',
    'AiDisposeMaterialStrategyTitle', 'AiDisposeLifeStrategyTitle',
    'AiDisposeScenicSpotTitle', 'AiDisposeHistoryStrategyTitle',
    'AiDisposeQATitle', 'AiDisposeIMGTitle', 'AiDisposeFoodStrategyTitle',
    'AiDisposeFestivalCustomsTitle',
)


class ConfirmationDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        source = Path(__file__).resolve().parents[1] / 'main.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        cls.method_codes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in METHODS:
                namespace = {}
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
                cls.method_codes[node.name] = namespace[node.name].__code__

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.input = Path(self.temp.name) / 'titles.xlsx'
        self.input.touch()
        self.window = QWidget()
        self.addCleanup(self.window.close)
        self.addCleanup(self.window.deleteLater)
        self.window.accountNameLineEdit = QLineEdit('test account', self.window)
        self.window.videoTypeComboBox = QComboBox(self.window)
        self.window.videoTypeComboBox.addItems(['景点介绍类', '美食介绍类'])
        self.window.videoTypeComboBox.setCurrentIndex(1)
        self.window.titleFileLabel = QLabel(str(self.input), self.window)
        self.window.copyFileLabel = QLabel('copy.xlsx', self.window)
        self.window.labelFilelabel = QLabel('labels.xlsx', self.window)
        self.window.saveVideoPathLabel = QLabel(self.temp.name, self.window)
        self.window.run_label = QLabel('', self.window)
        self.window.compositeVideoButton = QPushButton(self.window)
        for name in ('on_process_result_ready', 'on_success_occurred',
                     'on_error_occurred', 'compositeMsInforVideo', 'showModelSetList'):
            setattr(self.window, name, Mock())
        self.window.on_items_selection = Mock(return_value=[['test-template']])
        self.pool = SimpleNamespace(start=Mock())
        self.worker = SimpleNamespace(signals=SimpleNamespace(
            progressResultReady=Mock(), finished=Mock(), errorOccurred=Mock()))
        self.worker_types = {name: Mock(return_value=self.worker) for name in WORKERS}
        self.delete_template = Mock(return_value=True)
        self.namespace = dict(self.worker_types, os=os, QMessageBox=QMessageBox,
                              QThreadPool=SimpleNamespace(globalInstance=lambda: self.pool),
                              delete_video_model=self.delete_template)
        information = patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Ok)
        self.information = information.start()
        self.addCleanup(information.stop)

    def invoke(self, method, action):
        observations = []

        def respond():
            dialog = self.window.findChild(QMessageBox)
            if dialog is None:
                observations.append('missing dialog')
                return
            observations.append(action)
            if action == 'close':
                dialog.close()
            else:
                role = (QMessageBox.ButtonRole.AcceptRole if action == 'yes'
                        else QMessageBox.ButtonRole.RejectRole)
                for button in dialog.buttons():
                    if dialog.buttonRole(button) == role:
                        button.click()
                        return
                dialog.reject()

        # A guard prevents a broken test from blocking the entire test run.
        guard = QTimer(self.window)
        guard.setSingleShot(True)
        guard.timeout.connect(lambda: [box.reject() for box in self.window.findChildren(QMessageBox)])
        guard.start(3000)
        QTimer.singleShot(0, respond)
        try:
            types.FunctionType(self.method_codes[method], self.namespace)(self.window)
        finally:
            guard.stop()
        self.assertEqual(observations, [action])

    def test_ai_yes_starts_selected_worker_once_and_sets_outputs(self):
        self.invoke('aiDisposeTitle', 'yes')
        self.worker_types['AiDisposeMsIntroTitle'].assert_called_once_with(str(self.input), 'test account')
        self.pool.start.assert_called_once_with(self.worker)
        self.worker.signals.progressResultReady.connect.assert_called_once_with(self.window.on_process_result_ready)
        self.assertEqual(self.window.copyFileLabel.text(), str(self.input.with_stem('titles_copy')))
        self.assertEqual(self.window.labelFilelabel.text(), str(self.input.with_stem('titles_label')))

    def assert_ai_cancelled(self, action):
        self.invoke('aiDisposeTitle', action)
        self.pool.start.assert_not_called()
        for factory in self.worker_types.values():
            factory.assert_not_called()
        self.assertEqual(self.window.copyFileLabel.text(), 'copy.xlsx')
        self.assertEqual(self.window.labelFilelabel.text(), 'labels.xlsx')

    def test_ai_no_does_not_start(self):
        self.assert_ai_cancelled('no')

    def test_ai_close_does_not_start(self):
        self.assert_ai_cancelled('close')

    def test_composition_yes_dispatches_selected_video_type(self):
        self.invoke('compositeVideo', 'yes')
        self.window.compositeMsInforVideo.assert_called_once_with(
            'copy.xlsx', 'labels.xlsx', self.temp.name, 'test account')
        self.assertTrue(self.window.compositeVideoButton.isEnabled())

    def assert_composition_cancelled(self, action):
        self.invoke('compositeVideo', action)
        self.window.compositeMsInforVideo.assert_not_called()
        self.assertTrue(self.window.compositeVideoButton.isEnabled())

    def test_composition_no_does_not_generate(self):
        self.assert_composition_cancelled('no')

    def test_composition_close_does_not_generate(self):
        self.assert_composition_cancelled('close')

    def test_template_yes_deletes_only_the_selected_template(self):
        self.invoke('video_model_delete', 'yes')
        self.delete_template.assert_called_once_with('test-template')
        self.window.showModelSetList.assert_called_once_with()
        self.information.assert_not_called()

    def assert_deletion_cancelled(self, action):
        self.invoke('video_model_delete', action)
        self.delete_template.assert_not_called()
        self.window.showModelSetList.assert_not_called()

    def test_template_no_does_not_delete(self):
        self.assert_deletion_cancelled('no')

    def test_template_close_does_not_delete(self):
        self.assert_deletion_cancelled('close')


@unittest.skipUnless(os.environ.get('PACKAGED_EXE_PATH'), 'Set PACKAGED_EXE_PATH to validate shipped entry points')
class PackagedConfirmationDialogTests(ConfirmationDialogTests):
    @classmethod
    def setUpClass(cls):
        from PyInstaller.archive.readers import CArchiveReader
        cls.app = QApplication.instance() or QApplication([])
        archive = CArchiveReader(os.environ['PACKAGED_EXE_PATH'])
        main_code = marshal.loads(archive.extract('main'))
        class_code = next(code for code in main_code.co_consts
                          if isinstance(code, types.CodeType) and code.co_name == 'BatchAICutter')
        cls.method_codes = {code.co_name: code for code in class_code.co_consts
                            if isinstance(code, types.CodeType) and code.co_name in METHODS}
        if set(cls.method_codes) != set(METHODS):
            raise AssertionError('The full-version EXE is missing confirmation entry methods')


if __name__ == '__main__':
    unittest.main()
