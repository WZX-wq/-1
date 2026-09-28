# 鲲穹 AI 创影灵境完整版

这是完整版视频批量生成工具的源代码和打包配置。完整版包含多种标题类型、素材下载、AI 文案、配音、字幕和视频合成流程。

## 本次修复

- 旧的豆包 `InvalidEndpoint.ClosedEndpoint` 调用已统一改为可配置的 OpenAI 兼容接口，默认使用 DeepSeek `deepseek-flash`。
- AI 密钥不再写入源码。运行前复制 `video_ai_config.example.json` 为程序目录下的 `video_ai_config.json`，填写密钥；也可以设置 `VIDEO_AI_API_KEY`、`VIDEO_AI_BASE_URL`、`VIDEO_AI_MODEL` 环境变量。
- 自动生成连续 3 次系统/API/网络错误会停止；当前标题只记录失败，不会误标记为已生成。
- 捕获 Python 内存错误、Windows 错误 1455 和页面文件不足，显示明确的内存不足处理提示并停止任务。
- `whisper` 和 `pandas` 改为按需导入，减少启动阶段的重型依赖加载。
- PyInstaller 配置继续使用 Qt 6.7、Server 2016 兼容 ICU/VC++ 运行库，并将 `tb.ico`、`soft_pic` 和配置模板加入发布包。

## AI 配置

不要把真实密钥提交到 Git。发布包中会带 `video_ai_config.example.json`，首次运行时在 `main.exe` 同级目录创建 `video_ai_config.json`：

```json
{
  "api_key": "你的 DeepSeek API 密钥",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-flash"
}
```

## 构建完整版

在 Windows x64、Python 3.12 和已经准备好的 Qt 6.7/Server 2016 运行时目录中运行：

```powershell
$env:PYTHONPATH = (Resolve-Path '.source-run-deps').Path
$env:LEGACY_PYQT_DIR = (Resolve-Path '.legacy-pyqt67').Path
pyinstaller --noconfirm main_legacy_compat.spec
```

发布时必须整体复制 `dist\main\`，不能只复制 `main.exe`；`_internal`、`soft_pic`、`endCredits`、音乐目录和 `ffmpeg-bin` 都是运行所需内容。当前仓库不提交本地虚拟环境、PyInstaller 输出和生成视频。

## 验证

```powershell
$env:PYTHONPATH = (Resolve-Path '.source-run-deps').Path
python -m unittest discover -s tests -p 'test*.py'
```

本地验证覆盖 95 项测试（其中 3 项按环境跳过）。当前只在 Windows 11 构建和启动验证过，Windows Server 2016 仍需在目标机器做最终实机验证。
