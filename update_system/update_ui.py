# 更新UI界面
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QTextEdit, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from typing import Dict, Optional
from .update_config import UpdateConfig
from .update_checker import UpdateChecker
from .update_downloader import UpdateDownloader
from .update_installer import UpdateInstaller


class UpdateThread(QThread):
    """更新线程"""
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, config: UpdateConfig, update_info: Dict, action: str):
        super().__init__()
        self.config = config
        self.update_info = update_info
        self.action = action  # 'download' or 'install'
        self.downloader = None
        self.installer = None

    def run(self):
        try:
            if self.action == 'download':
                self.downloader = UpdateDownloader(self.config)
                success = self.downloader.download_update(
                    self.update_info,
                    self._progress_callback
                )
                # download_update 现在主程序下载成功即返回True
                if success:
                    self.finished_signal.emit(True, "下载完成")
                else:
                    self.finished_signal.emit(False, "下载失败，请检查网络连接后重试")

            elif self.action == 'install':
                self.installer = UpdateInstaller(self.config)
                # install_update 现在返回 (bool, str)
                success, message = self.installer.install_update(self._install_progress_callback)
                self.finished_signal.emit(success, message)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"更新线程异常:\n{error_details}")
            self.finished_signal.emit(False, f"更新线程异常：{str(e)}")

    def _progress_callback(self, downloaded: int, total: int, message: str):
        """下载进度回调"""
        self.progress_signal.emit(downloaded, total, message)

    def _install_progress_callback(self, progress: int, message: str):
        """安装进度回调"""
        self.progress_signal.emit(progress, 100, message)

    def cancel(self):
        """取消操作"""
        if self.downloader:
            self.downloader.cancel()


class UpdateDialog(QDialog):
    """更新对话框"""

    def __init__(self, config: UpdateConfig, update_info: Dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.update_info = update_info
        self.update_thread = None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("软件更新")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("发现新版本")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 版本信息
        current_version_info = self.config.get_version_info()
        version_info = f"""
当前版本: {current_version_info['version']}
最新版本: {self.update_info.get('version', 'Unknown')}
发布日期: {self.update_info.get('build_date', 'Unknown')}
文件大小: {self._format_size(self.update_info.get('file_size', 0))}
"""
        version_label = QLabel(version_info)
        layout.addWidget(version_label)

        # 更新日志
        changelog_label = QLabel("更新内容:")
        changelog_font = QFont()
        changelog_font.setPointSize(10)
        changelog_font.setBold(True)
        changelog_label.setFont(changelog_font)
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setMaximumHeight(150)
        changelog_content = '\n'.join(
            f"• {item}" for item in self.update_info.get('changelog', [])
        )
        self.changelog_text.setPlainText(changelog_content)
        layout.addWidget(self.changelog_text)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # 按钮
        button_layout = QHBoxLayout()

        self.download_btn = QPushButton("下载更新")
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)

        self.install_btn = QPushButton("安装更新")
        self.install_btn.clicked.connect(self.start_install)
        self.install_btn.setVisible(False)
        button_layout.addWidget(self.install_btn)

        self.cancel_btn = QPushButton("稍后提醒")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def start_download(self):
        """开始下载"""
        self.download_btn.setEnabled(False)
        self.cancel_btn.setText("取消")
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("检查已存在的更新文件...")

        # 先检查是否已存在完整的更新文件
        self.downloader = UpdateDownloader(self.config)
        if self.downloader.check_existing_update(self.update_info):
            # 已存在完整文件，直接显示完成
            self.status_label.setText("检测到已存在的完整更新文件，跳过下载")
            self.progress_bar.setValue(100)
            self.download_finished(True, "已存在完整更新文件，跳过下载")
            return

        # 创建并启动下载线程
        self.update_thread = UpdateThread(
            self.config,
            self.update_info,
            'download'
        )
        self.update_thread.progress_signal.connect(self.update_progress)
        self.update_thread.finished_signal.connect(self.download_finished)
        self.update_thread.start()

    def start_install(self):
        """开始安装"""
        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("正在安装更新...")

        # 创建并启动安装线程
        self.update_thread = UpdateThread(
            self.config,
            self.update_info,
            'install'
        )
        self.update_thread.progress_signal.connect(self.update_progress)
        self.update_thread.finished_signal.connect(self.install_finished)
        self.update_thread.start()

    def update_progress(self, current: int, total: int, message: str):
        """更新进度"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def download_finished(self, success: bool, message: str):
        """下载完成"""
        self.progress_bar.setVisible(False)

        if success:
            self.status_label.setText("下载完成，可以安装了")
            self.download_btn.setVisible(False)
            self.install_btn.setVisible(True)
            self.cancel_btn.setText("稍后安装")

            # 询问是否立即安装
            reply = QMessageBox.question(
                self,
                "下载完成",
                "更新已下载完成，是否立即安装？\n（安装过程中程序将重启）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.start_install()
        else:
            self.status_label.setText(f"下载失败: {message}")
            self.download_btn.setEnabled(True)
            self.cancel_btn.setText("关闭")

    def install_finished(self, success: bool, message: str):
        """安装完成"""
        if success:
            QMessageBox.information(
                self,
                "更新成功",
                f"{message}\n程序将重启以完成更新"
            )

            # 执行更新
            installer = UpdateInstaller(self.config)
            installer.execute_update()
        else:
            # 显示详细的错误信息
            error_text = f"更新安装失败：\n\n{message}\n\n" \
                        f"程序将继续使用当前版本。\n\n" \
                        f"如需帮助，请查看 logs 目录下的日志文件。"
            
            QMessageBox.critical(
                self,
                "更新失败",
                error_text
            )
            self.accept()

    def closeEvent(self, a0):
        """关闭事件"""
        if self.update_thread and self.update_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认取消",
                "更新正在进行中，确定要取消吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.update_thread.cancel()
                self.update_thread.wait()
                a0.accept()
            else:
                a0.ignore()
        else:
            a0.accept()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        size = float(size_bytes)  # 转换为 float 进行计算
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


def check_and_show_update(parent=None) -> bool:
    """
    检查并显示更新对话框
    返回: 是否有更新
    """
    config = UpdateConfig()
    checker = UpdateChecker(config)

    has_update, update_info = checker.check_for_updates(force=True)

    if has_update and update_info:
        dialog = UpdateDialog(config, update_info, parent)
        dialog.exec()
        return True

    return False
