"""PyQt entry point for the standalone three-agriculture generator."""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path
from typing import Sequence

from PyQt6.QtCore import QObject, QPoint, QThread, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QIcon, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from database_tool.mysql_read_tool import DatabaseReadError
from sanong_generation.errors import (
    DatabaseWriteError,
    StartupConfigurationError,
    SystemGenerationError,
)
from sanong_generation.service import RunSummary
from sanong_generation.title_import import read_title_workbook
from sanong_runner import (
    _bootstrap_error,
    build_runtime,
    executable_dir,
    main as console_main,
)
from ui.new_batch_ai_autocut import Ui_new_batch_ai_autocut


WINDOW_TITLE = "鲲穹AI-创影灵境"


class _LogEmitter(QObject):
    message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    def __init__(self, parent: QObject | None = None):
        super().__init__()
        self.emitter = _LogEmitter(parent)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.emitter.message.emit(self.format(record))
        except Exception:
            self.handleError(record)


class GenerationWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        service,
        accounts: Sequence[str],
        allowed_titles: Sequence[str],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._service = service
        self._accounts = list(accounts)
        self._allowed_titles = tuple(allowed_titles)

    def run(self) -> None:
        try:
            self.succeeded.emit(
                self._service.run(self._accounts, self._allowed_titles)
            )
        except Exception as error:
            self.failed.emit(f"{error}\n{traceback.format_exc()}")


class TitleImportWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        repository,
        account_name: str,
        workbook_path: Path,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._repository = repository
        self._account_name = account_name
        self._workbook_path = Path(workbook_path)

    def run(self) -> None:
        try:
            titles = read_title_workbook(self._workbook_path)
            if not titles:
                raise ValueError("Excel 第一列没有可导入的标题")
            self.succeeded.emit(
                self._repository.import_titles(self._account_name, titles)
            )
        except Exception as error:
            self.failed.emit(f"{error}\n{traceback.format_exc()}")


class SanongMainWindow(QWidget, Ui_new_batch_ai_autocut):
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        self.worker: GenerationWorker | None = None
        self.import_worker: TitleImportWorker | None = None
        self.selected_title_path: Path | None = None
        self._titles_imported = False
        self._imported_account = ""
        self._imported_titles: tuple[str, ...] = ()
        self._stop_requested = False
        self._close_pending = False
        self._log_handler: QtLogHandler | None = None
        self._dragging = False
        self._drag_offset = QPoint()

        self.setupUi(self)
        self._configure_original_ui()
        self._install_log_handler()

    def _configure_original_ui(self) -> None:
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        icon_path = self._find_asset("tb.ico")
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))

        self._load_original_assets()
        self._configure_title_bar()
        self._configure_file_panel()
        self._configure_production_panel()
        self._configure_status_panel()

    def _find_asset(self, relative_path: str) -> Path | None:
        """Resolve mutable release assets, then PyInstaller's bundled copy."""
        candidates = [Path(self.runtime.config.base_dir) / relative_path]
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            candidates.append(Path(bundle_dir) / relative_path)
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        self.runtime.log.warning(
            "界面资源不存在: %s (查找位置: %s)",
            relative_path,
            ", ".join(str(path) for path in candidates),
        )
        return None

    def _load_original_assets(self) -> None:
        self.label_4.setText("")
        self.label_4.setFixedSize(24, 24)
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = self._find_asset("soft_pic/cylogo.png")
        if logo_path is not None:
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                self.label_4.setPixmap(
                    pixmap.scaled(
                        self.label_4.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.runtime.log.info("已加载窗口 logo: %s", logo_path)
            else:
                self.runtime.log.warning("窗口 logo 无法解析: %s", logo_path)

        buttons = (
            self.titleTypeButton,
            self.vioceSetButton,
            self.srtSetButton,
            self.productVideoButton,
            self.videoModelButton,
            self.aiSetButton,
        )
        for index, button in enumerate(buttons, start=1):
            name = "4-1.png" if index == 4 else f"{index}.png"
            image_path = self._find_asset(f"soft_pic/{name}")
            if image_path is not None:
                button.setIcon(QIcon(QPixmap(str(image_path))))

        for button in buttons:
            button.setEnabled(button is self.productVideoButton)
        self.productVideoButton.clicked.connect(lambda: self.tabWidget.setCurrentIndex(3))

    def _configure_title_bar(self) -> None:
        self.minBtn.clicked.connect(self.showMinimized)
        self.maxBtn.clicked.connect(self._toggle_maximize)
        self.closeBtn.clicked.connect(self.close)
        self.widget.mousePressEvent = self._on_drag_press
        self.widget.mouseMoveEvent = self._on_drag_move
        self.widget.mouseReleaseEvent = self._on_drag_release

    def _configure_file_panel(self) -> None:
        self.videoModelSetComboBox.clear()
        self.videoModelSetComboBox.addItem("三农账号配置")
        self.videoModelSetComboBox.setEnabled(False)

        self.accountNameLineEdit.hide()
        self.accountNameComboBox = QComboBox(self.widget_2)
        self.accountNameComboBox.setObjectName("accountNameComboBox")
        self.accountNameComboBox.setGeometry(self.accountNameLineEdit.geometry())
        self.accountNameComboBox.setStyleSheet(
            "background-color: rgb(56, 56, 56);"
            "color: rgb(153, 153, 153);"
        )
        self.accountNameComboBox.addItems(self.runtime.accounts)
        self.accountNameComboBox.currentTextChanged.connect(
            self._invalidate_import_scope
        )
        self.accountNameComboBox.show()

        self.videoTypeComboBox.clear()
        self.videoTypeComboBox.addItem("三农素材通用")
        self.videoTypeComboBox.setEnabled(False)

        self.copyFileLabel.setText("请先导入标题")
        self.labelFilelabel.setText("导入后点击开始")
        self.openCopyFileButton.hide()
        self.openLabelFileButton.hide()

        self.aiProductButton.setText("导入标题")
        self.openTilteFileButton.clicked.connect(self.select_title_workbook)
        self.aiProductButton.clicked.connect(self.import_selected_titles)

        self.run_label.setReadOnly(True)
        self.run_label.clear()
        self.run_label.document().setMaximumBlockCount(5000)
        self.run_label.setStyleSheet(
            "background-color: rgb(39, 40, 42); color: rgb(153, 153, 153);"
        )

    def _configure_production_panel(self) -> None:
        self.tabWidget.setCurrentIndex(3)
        self.tabWidget.tabBar().hide()

        output_path = str(self.runtime.config.output_dir)
        self.saveVideoPathLabel.setText(output_path)
        self.saveVideoPathLabel.setToolTip(output_path)
        self.saveVideoToolButton.hide()

        screen = getattr(self.runtime.config, "screen", "vertical")
        self.screenComboBox.setCurrentIndex(1 if screen == "horizontal" else 0)
        self.screenComboBox.setEnabled(False)
        self.randomVideoModelCheckBox.setChecked(
            bool(getattr(self.runtime.config, "random_video_model", True))
        )
        self.randomVideoModelCheckBox.setEnabled(False)

        for control in (
            self.label_104,
            self.locationlineEdit,
            self.label_102,
            self.endVideoPathLabel,
            self.endVideoToolButton,
            self.label_106,
            self.compositeTimeSpinBox,
            self.uploadCheckBox,
        ):
            control.hide()

        self.compositeVideoButton.setText("停止生成")
        self.compositeVideoButton.setEnabled(False)
        self.compositeVideoButton.clicked.connect(self.request_stop)
        self.stop_button = self.compositeVideoButton

        self.autoGenerateButton.setCheckable(False)
        self.autoGenerateButton.setText("开启自动生成")
        self.autoGenerateButton.setEnabled(False)
        self.autoGenerateButton.clicked.connect(self.start_generation)
        self.start_button = self.autoGenerateButton

    def _configure_status_panel(self) -> None:
        for child in self.widget_13.findChildren(
            QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
        ):
            child.hide()

        heading = QLabel("运行状态", self.widget_13)
        heading.setGeometry(30, 10, 100, 24)
        heading.setStyleSheet("color: white; font: 11pt 'SimHei';")

        line = QFrame(self.widget_13)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setGeometry(20, 38, 591, 2)
        line.setStyleSheet("color: rgb(88, 88, 88);")

        status_caption = QLabel("当前状态", self.widget_13)
        status_caption.setGeometry(30, 58, 80, 24)
        status_caption.setStyleSheet("color: white; font: 10pt 'SimHei';")
        self.status_value_label = QLabel("准备就绪", self.widget_13)
        self.status_value_label.setGeometry(115, 50, 470, 45)
        self.status_value_label.setWordWrap(True)
        self.status_value_label.setStyleSheet(
            "color: rgb(19, 171, 234); font: 10pt 'SimHei';"
        )

        self.generated_value_label = self._create_metric(
            30, "生成成功", "0", "rgb(82, 196, 128)"
        )
        self.failed_value_label = self._create_metric(
            220, "标题失败", "0", "rgb(234, 104, 104)"
        )
        self.exhausted_value_label = self._create_metric(
            410,
            "标题耗尽",
            f"0 / {len(self.runtime.accounts)}",
            "rgb(237, 190, 82)",
        )

        self.output_button = QPushButton("打开输出目录", self.widget_13)
        self.output_button.setGeometry(110, 270, 130, 40)
        self.output_button.clicked.connect(
            lambda: self._open_directory(Path(self.runtime.config.output_dir))
        )
        self.log_button = QPushButton("打开日志目录", self.widget_13)
        self.log_button.setGeometry(390, 270, 130, 40)
        self.log_button.clicked.connect(
            lambda: self._open_directory(Path(self.runtime.config.base_dir) / "logs")
        )
        button_style = (
            "QPushButton { background-color: rgb(19, 171, 234); color: white;"
            "border: 1px solid rgb(88, 88, 88); border-radius: 5px; }"
            "QPushButton:hover { border: 2px solid rgb(255, 255, 127); }"
        )
        self.output_button.setStyleSheet(button_style)
        self.log_button.setStyleSheet(button_style)

    def _create_metric(self, x: int, title: str, value: str, color: str) -> QLabel:
        title_label = QLabel(title, self.widget_13)
        title_label.setGeometry(x, 120, 100, 24)
        title_label.setStyleSheet("color: rgb(153, 153, 153); font: 10pt 'SimHei';")
        value_label = QLabel(value, self.widget_13)
        value_label.setGeometry(x, 150, 150, 40)
        value_label.setStyleSheet(f"color: {color}; font: 18pt 'SimHei';")
        return value_label

    def _install_log_handler(self) -> None:
        handler = QtLogHandler(self)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        handler.emitter.message.connect(self._append_log)
        self.runtime.log.addHandler(handler)
        self._log_handler = handler

    def _append_log(self, message: str) -> None:
        self.run_label.append(message)
        scrollbar = self.run_label.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def select_title_workbook(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择三农标题 Excel",
            "",
            "Excel 工作簿 (*.xlsx)",
        )
        if not selected:
            return
        self._invalidate_import_scope()
        self.selected_title_path = Path(selected)
        self.titleFileLabel.setText(selected)
        self.titleFileLabel.setToolTip(selected)
        self._set_status("已选择标题文件，点击“导入标题”写入当前账号")

    def import_selected_titles(self) -> None:
        if self.selected_title_path is None:
            self._set_status("请先选择标题文件")
            return
        account_name = self.accountNameComboBox.currentText().strip()
        if not account_name:
            self._set_status("没有可用账号，请检查账号配置")
            return
        if not self.selected_title_path.is_file():
            self._set_status("标题文件不存在，请重新选择")
            return
        if self._generation_running():
            self._set_status("正在生成视频，暂时不能导入标题")
            return
        if self.import_worker is not None and self.import_worker.isRunning():
            return

        self._invalidate_import_scope()
        self._set_status("正在读取并导入标题")
        self._set_import_busy(True)
        worker = TitleImportWorker(
            self.runtime.repository,
            account_name,
            self.selected_title_path,
            self,
        )
        worker.succeeded.connect(self._import_succeeded)
        worker.failed.connect(self._import_failed)
        worker.finished.connect(self._import_finished)
        self.import_worker = worker
        self.runtime.log.info(
            "开始导入三农标题，账号: %s，文件: %s",
            account_name,
            self.selected_title_path,
        )
        worker.start()

    def _import_succeeded(self, summary) -> None:
        self._imported_account = str(summary.account_name).strip()
        self._imported_titles = tuple(summary.titles)
        self._titles_imported = bool(
            self._imported_account and self._imported_titles
        )
        message = (
            f"标题导入完成：成功导入 {summary.inserted} 条，"
            f"跳过 {summary.duplicates} 条重复"
        )
        self._set_status(message)
        self.runtime.log.info(
            "标题导入完成: 读取 %d 条，成功 %d 条，重复 %d 条；"
            "本次生成仅限这 %d 条标题",
            summary.read,
            summary.inserted,
            summary.duplicates,
            len(self._imported_titles),
        )

    def _invalidate_import_scope(self, *_args) -> None:
        if self._generation_running():
            return
        self._titles_imported = False
        self._imported_account = ""
        self._imported_titles = ()
        if hasattr(self, "autoGenerateButton"):
            self.autoGenerateButton.setEnabled(False)

    def _import_failed(self, detail: str) -> None:
        message = detail.splitlines()[0] if detail else "未知错误"
        self._set_status(f"标题导入失败：{message}")
        self.runtime.log.error("标题导入失败: %s", detail)

    def _import_finished(self) -> None:
        worker = self.import_worker
        self.import_worker = None
        self._set_import_busy(False)
        if worker is not None:
            worker.deleteLater()
        self._close_when_idle()

    def _set_import_busy(self, busy: bool) -> None:
        self.aiProductButton.setEnabled(not busy)
        self.openTilteFileButton.setEnabled(not busy)
        self.accountNameComboBox.setEnabled(not busy)
        self.autoGenerateButton.setEnabled(
            self._titles_imported and not busy and not self._generation_running()
        )

    def start_generation(self) -> None:
        if self._generation_running():
            return
        if self.import_worker is not None and self.import_worker.isRunning():
            self._set_status("正在导入标题，请稍候")
            return
        if not self._titles_imported:
            self._set_status("请先导入标题")
            return
        if not self._imported_account:
            self._set_status("没有可用账号，请检查账号配置")
            return

        accounts = [self._imported_account]
        self._stop_requested = False
        self._set_status("运行中")
        self.generated_value_label.setText("0")
        self.failed_value_label.setText("0")
        self.exhausted_value_label.setText("0 / 1")
        self.autoGenerateButton.setEnabled(False)
        self.aiProductButton.setEnabled(False)
        self.openTilteFileButton.setEnabled(False)
        self.accountNameComboBox.setEnabled(False)
        self.stop_button.setEnabled(True)

        worker = GenerationWorker(
            self.runtime.service,
            accounts,
            self._imported_titles,
            self,
        )
        worker.succeeded.connect(self._generation_succeeded)
        worker.failed.connect(self._generation_failed)
        worker.finished.connect(self._worker_finished)
        self.worker = worker
        self.runtime.log.info(
            "开始生成本次导入的三农标题，账号: %s，标题范围: %d 条",
            self._imported_account,
            len(self._imported_titles),
        )
        worker.start()

    def request_stop(self) -> None:
        if not self._generation_running():
            return
        self._stop_requested = True
        self._set_status("正在停止")
        self.stop_button.setEnabled(False)
        self.runtime.log.info("正在停止，将在当前标题处理结束后退出")
        self.runtime.service.request_stop()

    def _generation_succeeded(self, summary: RunSummary) -> None:
        self.generated_value_label.setText(str(summary.generated))
        self.failed_value_label.setText(str(summary.title_failures))
        self.exhausted_value_label.setText(
            f"{summary.exhausted_accounts} / {summary.accounts}"
        )
        if self._stop_requested:
            self._set_status("任务已停止")
        elif summary.accounts and summary.exhausted_accounts == summary.accounts:
            self._set_status("任务完成，所有账号均无可用三农标题")
        else:
            self._set_status("任务完成")
        self.runtime.log.info(
            "生成结束: 成功 %d，标题失败 %d，已耗尽账号 %d/%d",
            summary.generated,
            summary.title_failures,
            summary.exhausted_accounts,
            summary.accounts,
        )

    def _generation_failed(self, detail: str) -> None:
        message = detail.splitlines()[0] if detail else "未知错误"
        self._set_status(f"运行失败：{message}")
        self.runtime.log.error("三农生成任务失败: %s", detail)
        if message.startswith("内存不足："):
            QMessageBox.critical(self, "内存不足", message)
        elif message.startswith("磁盘空间不足"):
            QMessageBox.warning(self, "磁盘空间不足", message)

    def _worker_finished(self) -> None:
        worker = self.worker
        self.worker = None
        self.autoGenerateButton.setText("再次运行")
        self.autoGenerateButton.setEnabled(
            self._titles_imported and self.import_worker is None
        )
        self.aiProductButton.setEnabled(self.import_worker is None)
        self.openTilteFileButton.setEnabled(self.import_worker is None)
        self.accountNameComboBox.setEnabled(self.import_worker is None)
        self.stop_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()
        self._close_when_idle()

    def _generation_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def _set_status(self, message: str) -> None:
        self.status_value_label.setText(message)

    def _open_directory(self, path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
        except OSError as error:
            opened = False
            self.runtime.log.error("无法打开目录 %s: %s", path, error)
        if not opened:
            self.runtime.log.warning("系统未能打开目录: %s", path)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.maxBtn.setText("□")
        else:
            self.showMaximized()
            self.maxBtn.setText("❐")

    def _on_drag_press(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _on_drag_move(self, event: QMouseEvent) -> None:
        if self._dragging and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def _on_drag_release(self, event: QMouseEvent) -> None:
        self._dragging = False
        event.accept()

    def _close_when_idle(self) -> None:
        importing = self.import_worker is not None and self.import_worker.isRunning()
        if self._close_pending and not self._generation_running() and not importing:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event: QCloseEvent) -> None:
        importing = self.import_worker is not None and self.import_worker.isRunning()
        if self._generation_running() or importing:
            self._close_pending = True
            if self._generation_running():
                self.request_stop()
            event.ignore()
            return
        if self._log_handler is not None:
            self.runtime.log.removeHandler(self._log_handler)
            self._log_handler = None
        event.accept()


def _show_startup_error(message: str) -> None:
    _bootstrap_error(message)
    QMessageBox.critical(None, WINDOW_TITLE, message)


def _build_gui_runtime():
    """Build local runtime without blocking the first window on the database."""
    return build_runtime(executable_dir())


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" in args:
        return console_main(args)

    app = QApplication.instance() or QApplication([sys.argv[0], *args])
    app.setApplicationName(WINDOW_TITLE)
    try:
        # A database health check can wait through several network timeouts on
        # a computer outside the server network. The GUI must be usable before
        # that remote dependency is contacted; import/generation workers still
        # report database errors at the operation that needs the connection.
        runtime = _build_gui_runtime()
    except StartupConfigurationError as error:
        _show_startup_error(f"启动配置错误: {error}")
        return 2
    except (DatabaseReadError, DatabaseWriteError, SystemGenerationError) as error:
        _show_startup_error(f"运行失败: {error}")
        return 1
    except Exception as error:
        _show_startup_error(f"未处理的运行错误: {error}\n{traceback.format_exc()}")
        return 1

    window = SanongMainWindow(runtime)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
