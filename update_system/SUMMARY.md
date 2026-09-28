# 📦 自动更新系统 - 完整功能总结

## 🎯 系统概述

为您的 BatchAiCutter 项目定制开发的完整自动更新解决方案，支持：
- ✅ **主程序更新** - 自动更新打包的 exe 文件
- ✅ **资源文件更新** - 批量更新本地资源文件夹
- ✅ **配置文件管理** - 智能管理用户配置
- ✅ **完整性校验** - SHA256 文件校验
- ✅ **自动备份回滚** - 更新失败自动恢复

## 📁 文件结构

```
update_system/
├── __init__.py                 # 模块入口，导出主要功能
├── update_config.py            # 配置管理（版本号、服务器地址、资源列表）
├── update_checker.py           # 更新检查（支持自定义服务器和GitHub）
├── update_downloader.py        # 并行下载（主程序+资源包）
├── update_installer.py         # 安装管理（备份、替换、回滚）
├── update_ui.py                # PyQt6 UI界面
├── README.md                   # 完整文档
├── QUICK_START.md              # 快速开始指南
├── SUMMARY.md                  # 本文件
└── example_integration.py      # 集成示例代码

辅助工具:
├── setup_updater.py            # 配置向导
└── create_update_package.py    # 更新包创建工具
```

## 🚀 核心功能

### 1. 更新检查 (update_checker.py)

**支持两种更新源：**

#### 方式A: 自定义服务器
```python
UPDATE_SERVER_URL = "https://your-server.com/api"
```

API端点：
- `GET /manifest.json` - 获取更新清单

#### 方式B: GitHub Releases
```python
GITHUB_REPO = "username/batchAiCutter"
```

自动从最新 Release 获取更新信息

**智能检查策略：**
- 语义化版本比较
- 可配置检查间隔（默认24小时）
- 支持强制检查
- 缓存最新版本信息

### 2. 并行下载 (update_downloader.py)

**下载管理：**
- ✅ 主程序 exe 文件
- ✅ 多个资源压缩包（并行下载）
- ✅ 实时进度回调
- ✅ 断点续传支持
- ✅ SHA256 完整性校验

**可配置资源文件夹：**
```python
RESOURCE_FOLDERS = [
    "cacheMusic",      # 音乐资源1
    "cacheMusic1",     # 音乐资源2
    "cacheMusic2",     # 音乐资源3
    "material",        # 素材文件
    "gifMaterial",     # GIF素材
    "soft_pic",        # 软件图片
    "touristPictures", # 旅游图片
    "endCredits",      # 片尾字幕
    "coverPicMaterial" # 封面图片
]
```

### 3. 安装管理 (update_installer.py)

**更新流程：**
```
1. 创建备份（保留最近3个版本）
   ├── 备份主程序 exe
   ├── 备份资源文件夹
   └── 备份配置文件

2. 准备更新文件
   ├── 验证新程序
   └── 解压资源包

3. 应用更新
   ├── 替换资源文件
   └── 创建更新脚本

4. 重启程序
   ├── 执行更新脚本
   ├── 替换主程序
   └── 启动新版本

5. 清理临时文件
```

**失败自动回滚：**
- 任何步骤失败都会触发回滚
- 自动从备份恢复所有文件
- 保证系统稳定性

### 4. UI界面 (update_ui.py)

**功能完善的对话框：**
- 📊 版本信息展示
- 📝 更新日志显示
- 📈 下载进度条
- 🔄 实时状态提示
- 🎛️ 操作按钮（下载/安装/取消）

**用户友好：**
- 非阻塞式更新检查
- 可选择稍后更新
- 清晰的操作指引

## 🛠️ 使用方法

### 快速集成（3步）

#### 步骤1: 配置系统

```bash
python setup_updater.py
```

按提示完成配置，生成：
- `update_config.json` - 运行配置
- `version.json` - 版本信息

#### 步骤2: 集成到主程序

在 `main.py` 中添加：

```python
class BatchAiCutter(QWidget):
    def __init__(self):
        super().__init__()
        # ... 现有代码 ...
        
        # 添加自动更新检查
        self.auto_check_update()
    
    def auto_check_update(self):
        """自动检查更新"""
        try:
            from update_system.update_ui import check_and_show_update
            from update_system.update_config import UpdateConfig
            from update_system.update_checker import UpdateChecker
            
            config = UpdateConfig()
            config_data = config.load_config()
            
            if config_data.get('auto_check_update', True):
                checker = UpdateChecker(config)
                if checker.should_check_update():
                    has_update, update_info = checker.check_for_updates()
                    if has_update:
                        from update_system.update_ui import UpdateDialog
                        dialog = UpdateDialog(config, update_info, self)
                        dialog.show()
        except Exception as e:
            print(f"检查更新失败: {e}")
```

#### 步骤3: 创建更新包

```bash
python create_update_package.py
```

选择要打包的资源，自动生成：
- 资源压缩包（.zip）
- 更新清单（manifest.json）
- SHA256 校验和

## 📋 配置说明

### update_config.json

```json
{
    "auto_check_update": true,        // 自动检查更新
    "auto_download_update": false,    // 自动下载（推荐false）
    "update_channel": "stable",       // 更新通道
    "check_interval_hours": 24,       // 检查间隔
    "download_threads": 4,            // 下载线程数
    "enable_incremental_update": true,// 增量更新
    "backup_before_update": true      // 更新前备份
}
```

### manifest.json（服务器端）

```json
{
    "version": "1.1.0",
    "build_date": "2024-01-15T10:00:00",
    "description": "新版本发布",
    "changelog": [
        "新增功能A",
        "修复Bug B"
    ],
    "download_url": "https://server.com/main_v1.1.0.exe",
    "file_size": 491560960,
    "checksum": "sha256-hash",
    "min_version": "1.0.0",
    "force_update": false,
    "resources": [
        {
            "name": "music_v1.1.zip",
            "url": "https://server.com/music_v1.1.zip",
            "size": 85000000,
            "checksum": "sha256-hash",
            "type": "music"
        }
    ]
}
```

## 🔒 安全特性

1. **文件完整性**
   - SHA256 校验和验证
   - 下载失败自动重试
   - 文件大小验证

2. **备份机制**
   - 更新前自动备份
   - 保留最近3个版本
   - 失败自动回滚

3. **权限管理**
   - 更新脚本验证
   - 文件访问检查
   - 进程安全退出

## 📊 更新流程图

```
[用户启动程序]
       ↓
[自动检查更新?] → 否 → [正常运行]
       ↓ 是
[连接更新服务器]
       ↓
[比较版本号]
       ↓
[有新版本?] → 否 → [正常运行]
       ↓ 是
[显示更新对话框]
       ↓
[用户选择下载]
       ↓
[并行下载文件]
   ├─ 主程序exe
   ├─ 音乐资源包
   ├─ 素材资源包
   └─ 其他资源
       ↓
[校验文件完整性]
       ↓
[询问是否安装]
       ↓
[创建备份]
       ↓
[准备更新文件]
       ↓
[创建更新脚本]
       ↓
[重启程序]
       ↓
[批处理脚本执行]
   ├─ 等待程序退出
   ├─ 替换主程序
   ├─ 更新资源文件
   └─ 启动新版本
       ↓
[更新完成]
```

## 🎨 自定义扩展

### 添加新的资源类型

编辑 `update_config.py`:

```python
RESOURCE_FOLDERS = [
    # ... 现有文件夹 ...
    "new_folder",  # 新增文件夹
]
```

### 自定义UI主题

编辑 `update_ui.py`:

```python
class UpdateDialog(QDialog):
    def init_ui(self):
        # 自定义样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
            }
        """)
```

### 添加更新前/后钩子

编辑 `update_installer.py`:

```python
def install_update(self, progress_callback=None):
    # 更新前钩子
    self._before_update_hook()
    
    # 执行更新
    # ...
    
    # 更新后钩子
    self._after_update_hook()

def _before_update_hook(self):
    """更新前执行"""
    # 保存用户数据
    # 关闭数据库连接
    pass

def _after_update_hook(self):
    """更新后执行"""
    # 迁移用户数据
    # 更新数据库架构
    pass
```

## 🐛 故障排除

### 常见问题

**Q: 更新检查失败**
```
原因: 网络连接问题或服务器不可用
解决: 检查网络，验证服务器地址
```

**Q: 下载中断**
```
原因: 网络不稳定
解决: 重新下载，系统会自动清理临时文件
```

**Q: 安装失败**
```
原因: 磁盘空间不足或权限问题
解决: 检查磁盘空间和文件权限，系统会自动回滚
```

**Q: 程序无法启动**
```
原因: 更新文件损坏
解决: 从备份文件夹手动恢复
```

## 📈 性能优化

- **并行下载**: 4个线程同时下载资源
- **增量更新**: 只下载变更的文件
- **压缩传输**: 资源文件zip压缩
- **智能缓存**: 版本信息本地缓存

## 📝 开发计划

未来功能：
- [ ] 差分更新（只下载变更部分）
- [ ] 断点续传优化
- [ ] 更新包签名验证
- [ ] 多语言支持
- [ ] 更新统计分析

## 💡 最佳实践

1. **版本管理**
   - 使用语义化版本号
   - 详细的更新日志
   - 清晰的发布说明

2. **测试流程**
   - 本地测试更新流程
   - 验证备份恢复功能
   - 检查资源文件完整性

3. **用户体验**
   - 非强制更新（除非必要）
   - 提供稍后更新选项
   - 清晰的进度提示

4. **安全性**
   - 使用HTTPS传输
   - 文件完整性校验
   - 更新包签名（推荐）

## 📞 技术支持

- 📖 查看 [完整文档](README.md)
- 🚀 参考 [快速开始](QUICK_START.md)
- 💻 查看 [示例代码](example_integration.py)

---

**开发团队**: BatchAiCutter Team  
**版本**: 1.0.0  
**最后更新**: 2024-01
