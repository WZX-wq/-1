# 🚀 快速开始指南

## 1分钟快速配置

### 步骤 1: 运行配置向导

```bash
python setup_updater.py
```

按照提示配置更新系统，这将自动生成必要的配置文件。

### 步骤 2: 在主程序中集成

在 `main.py` 的 `BatchAiCutter` 类中添加以下代码：

```python
# 在 __init__ 方法末尾添加
def __init__(self):
    # ... 现有初始化代码 ...
    
    # 自动检查更新
    self.auto_check_update()

# 添加更新方法
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
                if has_update and update_info:
                    from update_system.update_ui import UpdateDialog
                    dialog = UpdateDialog(config, update_info, self)
                    dialog.show()
    except Exception as e:
        print(f"检查更新失败: {e}")
```

### 步骤 3: 创建第一个更新包

```bash
python create_update_package.py
```

按照提示创建更新包和清单文件。

## 完整示例

### 使用自定义服务器

1. **配置服务器地址**
   
   编辑 `update_system/update_config.py`:
   ```python
   UPDATE_SERVER_URL = "https://your-server.com/api"
   ```

2. **部署 manifest.json**
   
   上传到: `https://your-server.com/api/manifest.json`

3. **上传更新文件**
   
   - 主程序: `https://your-server.com/downloads/main_v1.1.0.exe`
   - 资源包: `https://your-server.com/resources/music_v1.1.zip`

### 使用 GitHub Releases

1. **配置仓库信息**
   
   编辑 `update_system/update_config.py`:
   ```python
   GITHUB_REPO = "yourusername/batchAiCutter"
   ```

2. **创建 Release**
   
   在 GitHub 上创建新 Release，Tag 格式: `v1.1.0`

3. **上传文件**
   
   - `main.exe` - 主程序
   - `resources_music_v1.1.zip` - 音乐资源包
   - `resources_material_v1.1.zip` - 素材资源包

## 测试更新流程

### 本地测试

1. **模拟旧版本**
   
   修改 `update_config.py`:
   ```python
   CURRENT_VERSION = "1.0.0"
   ```

2. **准备测试服务器**
   
   创建本地 manifest.json:
   ```json
   {
       "version": "1.1.0",
       "download_url": "http://localhost:8000/main.exe",
       ...
   }
   ```

3. **启动测试服务器**
   
   ```bash
   python -m http.server 8000
   ```

4. **运行程序测试**
   
   ```bash
   python main.py
   ```

## 常见问题

### Q: 如何跳过某个资源文件夹的更新？

A: 修改 `update_system/update_config.py` 中的 `RESOURCE_FOLDERS` 列表，移除不需要更新的文件夹。

### Q: 如何更改备份保留数量？

A: 在 `update_installer.py` 中调用 `cleanup_old_backups(keep_count=5)` 设置保留数量。

### Q: 如何禁用自动检查更新？

A: 修改 `update_config.json`:
```json
{
    "auto_check_update": false
}
```

### Q: 如何强制用户更新？

A: 在 manifest.json 中设置:
```json
{
    "force_update": true,
    "min_version": "1.0.0"
}
```

## 发布流程

### 完整发布流程

```bash
# 1. 更新版本号
# 编辑 update_system/update_config.py
CURRENT_VERSION = "1.1.0"

# 2. 打包程序
pyinstaller main.spec

# 3. 创建资源包
python create_update_package.py

# 4. 上传到服务器或 GitHub

# 5. 更新 manifest.json

# 6. 测试更新流程

# 7. 发布公告
```

## 最佳实践

✅ **DO**
- 在发布前充分测试更新流程
- 保持版本号语义化（主版本.次版本.修订版本）
- 在更新日志中详细说明变更内容
- 使用文件校验和验证完整性
- 保留最近几个版本的备份

❌ **DON'T**
- 不要跳过版本号
- 不要在没有备份的情况下更新
- 不要在manifest.json中使用绝对路径
- 不要忘记更新changelog
- 不要同时更新太多资源文件

## 下一步

1. 📖 阅读完整文档: [README.md](README.md)
2. 💻 查看集成示例: [example_integration.py](example_integration.py)
3. 🔧 自定义配置: 编辑 `update_config.py`
4. 🎨 自定义UI: 修改 `update_ui.py`

## 技术支持

遇到问题？
- 查看 [README.md](README.md) 故障排除章节
- 检查日志文件
- 验证配置文件格式
- 确认网络连接正常
