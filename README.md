# 鲲穹 AI 创影灵境完整版

这是完整版视频批量生成工具的源代码和打包配置。完整版包含多种标题类型、素材下载、AI 文案、配音、字幕和视频合成流程。

## 本次修复

- 旧的豆包 `InvalidEndpoint.ClosedEndpoint` 调用已统一改为可配置的 OpenAI 兼容接口，私人完整版使用已实测的豆包 Lite，并自动维护同档位模型版本。
- 公开源码不含 AI 密钥。私人构建可将本地 Key 编译进 EXE，复制整个发布目录后无需再填 Key；设置页和环境变量仍可覆盖内置配置。
- 自动生成连续 3 次系统/API/网络错误会停止；当前标题只记录失败，不会误标记为已生成。
- 捕获 Python 内存错误、Windows 错误 1455 和页面文件不足，显示明确的内存不足处理提示并停止任务。
- `whisper` 和 `pandas` 改为按需导入，减少启动阶段的重型依赖加载。
- PyInstaller 配置继续使用 Qt 6.7、Server 2016 兼容 ICU/VC++ 运行库，并将 `tb.ico`、`soft_pic` 和配置模板加入发布包。
- Windows 任务栏使用独立完整版 AppUserModelID，并在无边框窗口创建后绑定大/小原生图标，避免仅修复界面 Logo 而任务栏仍显示默认图标。

## AI 配置

2026-10-23 实际调用验证：旧版豆包 Key 可以调用 `doubao-seed-2-1-lite-260915`。
旧的 `doubao-seed-1-6-251015` 返回 `InvalidEndpoint.ClosedEndpoint`，这是模型端点关闭，与账号额度不足不同。

在软件的「AI 设置」中填写接口地址、模型名称和对应的 Key，点击「确认配置」即可保存到程序目录，后续请求立即使用新配置，无需重新打包或重启。
文案、话题、素材标签使用同一个配置，历史函数名中的 DeepSeek/豆包字样不再决定实际调用服务商。

豆包当前已实测的配置：

```json
{
  "api_key": "自己的火山方舟 API Key",
  "base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "model": "doubao-seed-2-1-lite-260915",
  "auto_update_model": true
}
```

豆包和 DeepSeek 的 Key 不能混用。模型列表查询成功只说明身份验证通过，实际可用性仍须用生成请求验证。
云服务长期使用需要账号保持有效余额；任何具体模型都可能被供应商升级或下线，届时可在 AI 设置中更换模型。
软件会明确区分余额不足、密钥失效和模型端点关闭，系统错误仍按连续失败计数停止，失败标题不会标记成功。

「自动更新同档位模型」默认开启：豆包每天首次 AI 任务查询官方模型目录，选择同系列、同档位、可输出文字且未退役的正式模型；实际生成成功后才保存新模型。
候选模型不可用时继续使用原模型；原模型报告关闭时立即重新查询，最多尝试两个候选，不会无限重试。
不会跨服务商、跨 Key 或从 Lite 自动升级到 Pro；价格仍以服务商届时公布的计费规则为准。
查询模型列表失败不阻断原模型调用，账号欠费或限流时不会靠轮换模型重复请求。
检查在 AI 任务中运行，不增加软件启动阶段的网络等待。DeepSeek `deepseek-flash` 属于官方滚动别名，由服务商维护版本。
可以取消勾选固定当前模型；设置 `VIDEO_AI_MODEL` 环境变量也会固定模型。
`video_ai_model_state.json` 只记录检查时间和已验证模型，不含密钥，已从 Git 排除。

如果需要从自己保留的旧版 EXE 迁移 Key，可在构建环境运行以下命令；该工具只读取旧版字节码，不运行旧 EXE，也不输出密钥，不覆盖已有配置：

```powershell
python tools/import_legacy_ai_config.py --legacy-exe "D:\\旧版\\main.exe" --output "D:\\新版\\video_ai_config.json" --provider doubao
```

本地 `video_ai_config.json` 已被 Git 忽略；真实 Key 不应写回源码或提交仓库。

公开构建不带 Key，需要在设置页填写自己的配置；私人构建内置默认 Key，不依赖外置 `video_ai_config.json`。
自动更新内置模型时仅保存模型设置，不把内置 Key 写到外部配置。更换服务商地址时不会把内置 Key 转发给其他地址。
不要把真实密钥提交到 Git。以下是使用其他服务商时的可选覆盖示例：

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
python tools/finalize_full_release.py dist/main
```

如需生成仅供自己/可信电脑使用的内置 Key 私人包，在构建前额外设置：

```powershell
$env:VIDEO_AI_EMBED_CONFIG = (Resolve-Path 'video_ai_config.json').Path
```

私人包构建完成后，使用 `python tools/finalize_full_release.py dist/main --private` 校验内置配置并加入私人版说明。

构建期间只在系统临时目录生成私有模块，编译进 EXE 后清理临时源码。公开构建不设置此变量。
客户端内置 Key 可以被提取，不是不可逆的加密保护；私人 EXE、ZIP 和构建缓存不得上传公开仓库。
如果需要公开分发且保护共享额度，应另行部署服务端鉴权代理，不能仅依靠客户端隐藏 Key。

发布时必须整体复制 `dist\main\`，不能只复制 `main.exe`；`_internal`、`soft_pic`、`endCredits`、音乐目录和 `ffmpeg-bin` 都是运行所需内容。当前仓库不提交本地虚拟环境、PyInstaller 输出和生成视频。

## 验证

```powershell
$env:PYTHONPATH = (Resolve-Path '.source-run-deps').Path
python -m unittest discover -s tests -p 'test*.py'
```

本地验证覆盖 119 项测试（发布依赖检查需要设置 PACKAGED_EXE_PATH，私人 Key 检查另需 PACKAGED_PRIVATE_AI_CONFIG；另有 2 项专属三农发布测试按环境跳过）。当前只在 Windows 11 构建和启动验证过，Windows Server 2016 仍需在目标机器做最终实机验证。
