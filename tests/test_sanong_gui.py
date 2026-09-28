import logging
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from openpyxl import Workbook
from PyQt6.QtWidgets import QApplication

from sanong_generation.repository import TitleImportSummary
from sanong_generation.service import RunSummary
from sanong_gui import SanongMainWindow, _build_gui_runtime


class ImmediateService:
    def __init__(self):
        self.calls = []

    def run(self, accounts, allowed_titles=None):
        self.calls.append((list(accounts), tuple(allowed_titles or ())))
        return RunSummary(
            accounts=len(accounts),
            generated=2,
            title_failures=1,
            exhausted_accounts=len(accounts),
        )

    def request_stop(self):
        pass


class BlockingService:
    def __init__(self):
        self.started = Event()
        self.released = Event()
        self.stop_requested = False

    def run(self, accounts, allowed_titles=None):
        self.started.set()
        self.released.wait(timeout=2)
        return RunSummary(
            accounts=len(accounts),
            generated=0,
            title_failures=0,
            exhausted_accounts=0,
        )

    def request_stop(self):
        self.stop_requested = True
        self.released.set()


class ImportRepository:
    def __init__(self):
        self.calls = []

    def import_titles(self, account_name, titles):
        self.calls.append((account_name, list(titles)))
        return TitleImportSummary(
            read=len(titles),
            inserted=len(titles),
            duplicates=0,
            account_name=account_name,
            titles=tuple(titles),
        )


class BlockingImportRepository(ImportRepository):
    def __init__(self):
        super().__init__()
        self.started = Event()
        self.released = Event()

    def import_titles(self, account_name, titles):
        self.started.set()
        self.released.wait(timeout=2)
        return super().import_titles(account_name, titles)


def make_runtime(service, accounts=None, repository=None):
    logger = logging.getLogger(f"sanong_gui_test_{id(service)}")
    logger.handlers.clear()
    logger.propagate = False
    return SimpleNamespace(
        config=SimpleNamespace(
            base_dir=Path.cwd(),
            output_dir=Path.cwd() / "output",
        ),
        accounts=["账号甲", "账号乙"] if accounts is None else accounts,
        repository=repository or ImportRepository(),
        service=service,
        log=logger,
    )


def write_workbook(path: Path, titles) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    for title in titles:
        sheet.append([title])
    workbook.save(path)
    workbook.close()
    return path


class SanongMainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_until(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.01)
        self.app.processEvents()
        return predicate()

    def test_gui_runtime_build_does_not_run_database_health_check(self):
        runtime = SimpleNamespace(repository=SimpleNamespace(health_check=Mock()))
        with patch("sanong_gui.build_runtime", return_value=runtime) as build:
            self.assertIs(_build_gui_runtime(), runtime)

        build.assert_called_once()
        runtime.repository.health_check.assert_not_called()

    def test_initial_state_reuses_original_production_page(self):
        window = SanongMainWindow(make_runtime(ImmediateService()))
        self.addCleanup(window.close)

        accounts = [
            window.accountNameComboBox.itemText(index)
            for index in range(window.accountNameComboBox.count())
        ]

        self.assertEqual(window.label.text(), "创影灵境")
        self.assertEqual(window.tabWidget.currentIndex(), 3)
        self.assertEqual(accounts, ["账号甲", "账号乙"])
        self.assertEqual(window.videoTypeComboBox.currentText(), "三农素材通用")
        self.assertEqual(window.openTilteFileButton.text(), "+添加")
        self.assertEqual(window.aiProductButton.text(), "导入标题")
        self.assertEqual(window.copyFileLabel.text(), "请先导入标题")
        self.assertEqual(window.labelFilelabel.text(), "导入后点击开始")
        self.assertEqual(window.status_value_label.text(), "准备就绪")
        self.assertFalse(window.autoGenerateButton.isEnabled())
        self.assertFalse(window.stop_button.isEnabled())

    def test_logo_loads_from_pyinstaller_bundle_when_release_asset_is_missing(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            bundled_logo = root_path / "bundle" / "soft_pic" / "cylogo.png"
            bundled_logo.parent.mkdir(parents=True)
            shutil.copy2(Path.cwd() / "soft_pic" / "cylogo.png", bundled_logo)
            runtime = make_runtime(ImmediateService())
            runtime.config.base_dir = root_path / "release"

            with patch.object(sys, "_MEIPASS", str(root_path / "bundle"), create=True):
                window = SanongMainWindow(runtime)
            self.addCleanup(window.close)

            pixmap = window.label_4.pixmap()
            self.assertIsNotNone(pixmap)
            self.assertFalse(pixmap.isNull())
            self.assertEqual((pixmap.width(), pixmap.height()), (24, 24))
            self.assertGreaterEqual(window.label_4.width(), 24)
            self.assertGreaterEqual(window.label_4.height(), 24)

    def test_default_startup_waits_for_manual_generation(self):
        service = ImmediateService()
        window = SanongMainWindow(make_runtime(service))
        self.addCleanup(window.close)
        window.show()

        self.app.processEvents()

        self.assertEqual(service.calls, [])
        self.assertEqual(window.status_value_label.text(), "准备就绪")
        self.assertEqual(window.copyFileLabel.text(), "请先导入标题")
        self.assertEqual(window.labelFilelabel.text(), "导入后点击开始")
        window.start_generation()
        self.assertEqual(service.calls, [])
        self.assertEqual(window.status_value_label.text(), "请先导入标题")

    def test_title_file_button_displays_selected_workbook(self):
        window = SanongMainWindow(make_runtime(ImmediateService()))
        self.addCleanup(window.close)
        selected = str(Path.cwd() / "标题.xlsx")

        with patch(
            "sanong_gui.QFileDialog.getOpenFileName",
            return_value=(selected, "Excel 工作簿 (*.xlsx)"),
        ):
            window.openTilteFileButton.click()

        self.assertEqual(window.titleFileLabel.text(), selected)
        self.assertEqual(window.selected_title_path, Path(selected))

    def test_import_selected_titles_uses_selected_account(self):
        repository = ImportRepository()
        window = SanongMainWindow(
            make_runtime(ImmediateService(), repository=repository),
        )
        self.addCleanup(window.close)

        with tempfile.TemporaryDirectory() as root:
            path = write_workbook(Path(root) / "文案.xlsx", ["标题一", "标题二"])
            window.selected_title_path = path
            window.titleFileLabel.setText(str(path))
            window.accountNameComboBox.setCurrentText("账号乙")
            window.import_selected_titles()
            self.assertTrue(self.wait_until(lambda: window.import_worker is None))

        self.assertEqual(repository.calls, [("账号乙", ["标题一", "标题二"])])
        self.assertIn("成功导入 2 条", window.status_value_label.text())
        self.assertTrue(window.autoGenerateButton.isEnabled())

    def test_import_requires_a_file_and_configured_account(self):
        window = SanongMainWindow(make_runtime(ImmediateService()))
        self.addCleanup(window.close)

        window.import_selected_titles()
        self.assertIn("请先选择标题文件", window.status_value_label.text())

        empty = SanongMainWindow(
            make_runtime(ImmediateService(), accounts=[])
        )
        self.addCleanup(empty.close)
        empty.selected_title_path = Path("标题.xlsx")
        empty.import_selected_titles()
        self.assertIn("没有可用账号", empty.status_value_label.text())

    def test_import_disables_generation_until_finished(self):
        repository = BlockingImportRepository()
        window = SanongMainWindow(
            make_runtime(ImmediateService(), repository=repository),
        )
        self.addCleanup(repository.released.set)
        self.addCleanup(window.close)

        with tempfile.TemporaryDirectory() as root:
            path = write_workbook(Path(root) / "文案.xlsx", ["标题一"])
            window.selected_title_path = path
            window.import_selected_titles()
            self.assertTrue(self.wait_until(repository.started.is_set))
            self.assertFalse(window.autoGenerateButton.isEnabled())
            self.assertFalse(window.aiProductButton.isEnabled())
            repository.released.set()
            self.assertTrue(self.wait_until(lambda: window.import_worker is None))

        self.assertTrue(window.autoGenerateButton.isEnabled())
        self.assertTrue(window.aiProductButton.isEnabled())

    def test_manual_run_shows_completion_summary_and_keeps_window_open(self):
        service = ImmediateService()
        window = SanongMainWindow(make_runtime(service))
        self.addCleanup(window.close)
        window.show()
        window._import_succeeded(
            TitleImportSummary(
                read=1,
                inserted=1,
                duplicates=0,
                account_name="账号乙",
                titles=("本次标题",),
            )
        )
        window._set_import_busy(False)
        window.start_generation()

        completed = self.wait_until(
            lambda: window.status_value_label.text().startswith("任务完成")
        )

        self.assertTrue(completed)
        self.assertEqual(service.calls, [(["账号乙"], ("本次标题",))])
        self.assertTrue(window.isVisible())
        self.assertEqual(window.generated_value_label.text(), "2")
        self.assertEqual(window.failed_value_label.text(), "1")
        self.assertEqual(window.exhausted_value_label.text(), "1 / 1")
        self.assertIn("所有账号均无可用三农标题", window.status_value_label.text())

    def test_memory_failure_shows_actionable_dialog(self):
        window = SanongMainWindow(make_runtime(ImmediateService()))
        self.addCleanup(window.close)
        message = "内存不足：请关闭其他程序后重试。"

        with patch("sanong_gui.QMessageBox.critical") as critical:
            window._generation_failed(f"{message}\nTraceback details")

        critical.assert_called_once_with(window, "内存不足", message)
        self.assertEqual(window.status_value_label.text(), f"运行失败：{message}")

    def test_disk_failure_shows_cleanup_dialog(self):
        window = SanongMainWindow(make_runtime(ImmediateService()))
        self.addCleanup(window.close)
        message = "磁盘空间不足：剩余 64 MB，请清理后重试。"

        with patch("sanong_gui.QMessageBox.warning") as warning:
            window._generation_failed(f"{message}\nTraceback details")

        warning.assert_called_once_with(window, "磁盘空间不足", message)
        self.assertEqual(window.status_value_label.text(), f"运行失败：{message}")

    def test_changing_account_requires_import_again(self):
        window = SanongMainWindow(make_runtime(ImmediateService()))
        self.addCleanup(window.close)
        window._import_succeeded(
            TitleImportSummary(
                read=1,
                inserted=0,
                duplicates=1,
                account_name="账号甲",
                titles=("本次标题",),
            )
        )
        window._set_import_busy(False)
        self.assertTrue(window.autoGenerateButton.isEnabled())

        window.accountNameComboBox.setCurrentText("账号乙")

        self.assertFalse(window.autoGenerateButton.isEnabled())

    def test_stop_button_requests_cooperative_stop(self):
        service = BlockingService()
        window = SanongMainWindow(make_runtime(service))
        self.addCleanup(service.released.set)
        self.addCleanup(window.close)

        window._import_succeeded(
            TitleImportSummary(
                read=1,
                inserted=1,
                duplicates=0,
                account_name="账号甲",
                titles=("本次标题",),
            )
        )
        window._set_import_busy(False)
        window.start_generation()
        self.assertTrue(self.wait_until(service.started.is_set))
        window.stop_button.click()

        self.assertTrue(service.stop_requested)
        self.assertEqual(window.status_value_label.text(), "正在停止")
        self.assertFalse(window.stop_button.isEnabled())
        self.assertTrue(
            self.wait_until(lambda: window.autoGenerateButton.isEnabled())
        )


if __name__ == "__main__":
    unittest.main()
