# 更新系统集成示例
"""
这个文件展示了如何在 main.py 中集成自动更新系统
"""

from PyQt6.QtWidgets import QMainWindow, QMenuBar, QMenu, QMessageBox
from PyQt6.QtGui import QAction
from update_system.update_ui import check_and_show_update


class MainWindowWithUpdate(QMainWindow):
    """
    集成了更新系统的主窗口示例
    """
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # 程序启动时自动检查更新（可选）
        self.auto_check_update()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("BatchAiCutter")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建菜单栏
        self.create_menus()
    
    def create_menus(self):
        """创建菜单"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 检查更新
        update_action = QAction("检查更新", self)
        update_action.setShortcut("Ctrl+U")
        update_action.setStatusTip("检查软件更新")
        update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(update_action)
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def auto_check_update(self):
        """自动检查更新（静默）"""
        try:
            from update_system.update_config import UpdateConfig
            from update_system.update_checker import UpdateChecker
            
            config = UpdateConfig()
            config_data = config.load_config()
            
            # 只有开启自动检查才执行
            if config_data.get('auto_check_update', True):
                checker = UpdateChecker(config)
                
                # 检查是否应该检查更新
                if checker.should_check_update():
                    has_update, update_info = checker.check_for_updates()
                    
                    if has_update and update_info:
                        # 发现更新，显示对话框
                        from update_system.update_ui import UpdateDialog
                        dialog = UpdateDialog(config, update_info, self)
                        dialog.show()
                    
        except Exception as e:
            print(f"自动检查更新失败: {e}")
    
    def check_for_updates(self):
        """手动检查更新"""
        try:
            has_update = check_and_show_update(self)
            
            if not has_update:
                QMessageBox.information(
                    self,
                    "检查更新",
                    "当前已是最新版本！"
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "检查更新失败",
                f"无法检查更新: {e}\n请稍后重试"
            )
    
    def show_about(self):
        """显示关于对话框"""
        from update_system.update_config import UpdateConfig
        
        config = UpdateConfig()
        version_info = config.get_version_info()
        
        about_text = f"""
<h2>BatchAiCutter</h2>
<p><b>版本:</b> {version_info['version']}</p>
<p><b>构建日期:</b> {version_info.get('build_date', 'Unknown')}</p>
<p><b>描述:</b> {version_info.get('description', '')}</p>
<br>
<p>批量AI视频剪辑工具</p>
"""
        
        QMessageBox.about(self, "关于 BatchAiCutter", about_text)


# ============================================
# 在现有 main.py 中添加以下代码
# ============================================

"""
1. 在 BatchAiCutter 类的 __init__ 方法中添加:

def __init__(self):
    super(BatchAiCutter, self).__init__()
    # ... 现有代码 ...
    
    # 添加更新检查（在UI初始化完成后）
    self.auto_check_update()

2. 添加更新相关方法:

def auto_check_update(self):
    '''自动检查更新'''
    try:
        from update_system.update_config import UpdateConfig
        from update_system.update_checker import UpdateChecker
        
        config = UpdateConfig()
        config_data = config.load_config()
        
        if config_data.get('auto_check_update', True):
            checker = UpdateChecker(config)
            
            if checker.should_check_update():
                has_update, update_info = checker.check_for_updates()
                
                if has_update and update_info:
                    from update_system.update_ui import UpdateDialog
                    dialog = UpdateDialog(config, update_info, self)
                    dialog.show()
    except Exception as e:
        print(f"自动检查更新失败: {e}")

def check_for_updates(self):
    '''手动检查更新'''
    try:
        from update_system.update_ui import check_and_show_update
        has_update = check_and_show_update(self)
        
        if not has_update:
            QMessageBox.information(
                self,
                "检查更新",
                "当前已是最新版本！"
            )
    except Exception as e:
        QMessageBox.warning(
            self,
            "检查更新失败",
            f"无法检查更新: {e}"
        )

3. 如果有菜单栏，添加更新菜单项:

# 在创建菜单的地方添加
update_action = QAction("检查更新", self)
update_action.triggered.connect(self.check_for_updates)
help_menu.addAction(update_action)
"""
