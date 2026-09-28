# 自动更新系统
"""
自动更新系统 - 支持exe和资源文件的完整更新解决方案

主要功能:
- 自动检查更新（支持自定义服务器和GitHub Releases）
- 并行下载更新包和资源文件
- 文件完整性校验（SHA256）
- 自动备份和回滚
- 友好的UI界面
- 语义化版本管理

快速开始:
    from update_system import check_and_show_update
    
    # 检查并显示更新
    check_and_show_update(parent_window)

配置:
    1. 运行 setup_updater.py 配置向导
    2. 在 main.py 中集成更新检查
    3. 使用 create_update_package.py 创建更新包

详细文档:
    - README.md - 完整文档
    - QUICK_START.md - 快速开始指南
    - example_integration.py - 集成示例
"""

from .update_config import UpdateConfig
from .update_checker import UpdateChecker
from .update_downloader import UpdateDownloader
from .update_installer import UpdateInstaller

# 导出UI功能
try:
    from .update_ui import UpdateDialog, check_and_show_update
    __all__ = [
        'UpdateConfig',
        'UpdateChecker', 
        'UpdateDownloader',
        'UpdateInstaller',
        'UpdateDialog',
        'check_and_show_update'
    ]
except ImportError:
    # PyQt6 未安装时的降级处理
    __all__ = [
        'UpdateConfig',
        'UpdateChecker',
        'UpdateDownloader',
        'UpdateInstaller'
    ]

# 版本信息
__version__ = "1.0.0"
__author__ = "BatchAiCutter Team"
__description__ = "自动更新系统 - 支持exe和资源文件更新"
