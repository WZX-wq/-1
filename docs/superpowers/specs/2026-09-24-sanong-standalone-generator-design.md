# 三农视频独立生成程序设计

## 目标

把现有主程序中标题类型 `6` 的三农视频生成流程提取为可复用服务，并生成一个可放在独立目录运行的 Windows 程序。程序启动后读取现有账号配置，持续生成三农视频，直到所有账号都没有当天可用的三农标题，然后自动退出。

支持范围固定为 Windows 10/11 x64 和 Windows Server 2016/2019/2022 x64。目标电脑无需安装 Python、FFmpeg、Qt 或 VC++ Redistributable，也无需管理员权限，但发布目录必须位于当前用户可写的位置，并且必须能访问现有数据库、AI、语音和素材网络服务。Windows 7、32 位 Windows、Windows ARM、macOS 和 Linux 不在本次范围。

独立程序必须与原主程序共享同一套三农业务实现，不能通过复制代码形成第二套逻辑，也不能通过隐藏完整主界面的方式伪装为独立程序。

## 当前行为

当前三农流程分散在以下位置：

- `main.py` 负责账号轮询、标题类型选择、三农分支调度和 `compositeMaterialStrategyVideo` 合成。
- `worker/ai_worker.py` 中的 `AiDisposeMaterialStrategyTitle` 负责生成文案和分段标签。
- `database_tool/video_load_tool.py` 负责按标签或随机查询三农素材、下载素材和分辨率处理。
- 配音、字幕、视频拼接和背景音乐由现有 worker 与 ffmpeg 工具完成。

主程序的自动生成次数来自界面控件，默认 50，无法直接满足“运行到三农标题耗尽”。三农合成还直接读取多个 QWidget 状态，并通过 QThreadPool 和嵌套事件循环等待 worker，因此不能直接作为无界面程序复用。

## 架构

新增 `sanong_generation` 包，承载三农专用编排和合成逻辑：

```text
sanong_generation/
  config.py       独立程序配置、账号配置发现和启动校验
  repository.py   类型 6 标题获取及成功/失败状态回写
  copywriter.py   三农文案和分段标签生成
  media_core.py   无 Qt 的配音、字幕、拼接和背景音乐核心
  composer.py     三农素材匹配、配音、字幕、拼接和背景音乐
  service.py      多账号轮询、失败策略和终止条件
sanong_runner.py  独立 exe 入口
```

现有数据库、AI、字幕、音视频和 Excel 工具继续作为共享底层能力使用。只有三农专用业务编排从 `main.py` 和 `worker/ai_worker.py` 中迁出；不会复制通用工具。

原 `main.py` 的类型 6 自动生成分支和手动“素材通用类”入口改为调用 `sanong_generation`。其他标题类型及界面行为保持不变。

## 运行流程

1. `sanong_runner.py` 把工作目录固定到 exe 所在目录，初始化容错控制台编码、日志和 FFmpeg 路径；独立进程不初始化或导入 Qt。
2. 加载 `sanong_runner.json`，扫描 `video_model_set/*.txt`，按文件名排序得到账号列表。
3. 校验每份账号配置以及背景音乐、FFmpeg、输出目录和数据库连接。
4. 从 `account_polling_index.txt` 指定的位置开始按账号轮询。
5. 每个账号只查询 `title_type = 6` 且当天可用的一条标题，不再进入原有的多类型优先级算法。
6. 已有有效文案与标签时复用数据库内容，否则调用三农文案服务生成 `_copy.xlsx` 和 `_label.xlsx` 并回写数据库。
7. 为每段文案生成配音和字幕，优先按 AI 标签查询三农素材，匹配不到时使用现有随机三农素材兜底。
8. 拼接视频、添加背景音乐、写入 `1.xls` 和 `video_id.xlsx`，返回实际生成文件路径。
9. 成功后标记标题已生成，并按当前自动生成行为为账号创建上传任务；类型 6 不执行额外 FTP 上传。
10. 单个账号无标题后从本次运行的活动账号集合移除。活动账号集合为空时写入汇总日志并以退出码 `0` 退出。

轮询不会使用一个无限的生成次数。标题查询必须区分“查询成功但无记录”和“数据库查询失败”，数据库失败不能导致正常耗尽退出。

## 配置与目录

发布目录结构：

```text
三农视频生成/
  三农视频生成.exe
  sanong_runner.json
  setting.txt
  video_model_set/
  cacheMusic1/
  _internal/
  output/                 运行时创建
  cacheAFRVideo/          运行时创建
  cacheCutVideo/          运行时创建
  temp_title/             运行时创建
  tempConcateVideo/       运行时创建
  notSuccess/             运行时创建
  logs/                   运行时创建
```

`sanong_runner.json` 提供独立程序专用且无需界面的选项，初始值为：

```json
{
  "screen": 0,
  "random_video_model": true,
  "create_upload_tasks": true,
  "max_consecutive_system_failures": 3,
  "output_dir": "output"
}
```

`screen = 0` 保持现有界面的默认竖屏行为。路径相对于 exe 目录解析，绝对路径继续兼容。

构建脚本复制当前 `setting.txt`、`video_model_set` 和 `cacheMusic1`，不得修改源配置。现有三农代码会检查 `end_video_path`，但实际没有把该片尾加入类型 6 视频；独立三农合成器移除这项无效校验，因此不复制或依赖账号配置中的片尾路径。其他视频类型继续保留原有片尾行为。输出统一写到 `output/<账号>/<YYYYMMDD>/`，使整个发布目录可以移动。

## 无 Qt 媒体核心

三农服务不创建 QWidget，不模拟按钮或下拉框，也不导入 PyQt6。原先从界面读取的值改为显式配置：屏幕方向、是否使用随机模板、是否创建上传任务和输出目录。

配音字幕、视频片段处理与拼接、背景音乐分别提取为普通同步函数。现有 `SaWorker`、`CompositeVideo` 和 `AddMusicWorker` 继续供主程序使用，但其 `run()` 只调用共享核心函数并把进度、成功和异常转换为 Qt 信号。独立程序直接调用核心函数，因此不需要 QThreadPool、Qt 事件循环、Qt DLL 或 ICU DLL。

合成核心直接返回生成结果，不再通过 GUI 状态或重新拼接文件名来推断是否成功。核心函数接受普通 Python 回调报告进度；未提供回调时保持静默。

## 错误处理

错误分为三类：

- 启动配置错误：配置 JSON 损坏、无账号配置、FFmpeg/背景音乐缺失。记录具体路径并以退出码 `2` 退出。
- 标题级错误：单条标题的 AI 内容为空、标签为空、素材不足、配音或合成失败。调用现有失败记录逻辑，写入 `notSuccess`，然后继续下一个标题。
- 系统级错误：数据库不可用、所有 AI 请求均不可用、共享运行库异常或无法写输出目录。有限重试后计入连续系统失败；达到 3 次时以退出码 `1` 停止，避免批量消耗标题。

数据库操作保持现有重试策略。没有标题是正常状态，不计为失败。日志同时输出到可见控制台和 `logs/三农生成.log`，每次结束记录账号数、成功数、标题失败数、耗尽账号数和运行时长。

## 启动检查

独立程序支持 `三农视频生成.exe --check`。该模式只执行以下只读检查，不领取标题或生成视频：

- runner 配置可解析；
- 至少存在一份有效账号配置；
- FFmpeg 与 ffprobe 可执行；
- 背景音乐资源存在；
- 输出及缓存目录可创建；
- 数据库可以连接并执行轻量查询。

检查成功返回 `0`，失败返回 `2` 并在控制台和日志中列出原因。

## 打包

新增 `sanong_runner.spec`，使用 PyInstaller onedir 模式输出到 `dist_sanong/三农视频生成/`。用户只需启动目录顶层的 `三农视频生成.exe`；Python、媒体运行库和 VC++ runtime 放在 `_internal`。

打包只从 `sanong_runner.py` 的依赖图收集模块，明确排除 PyQt6、whisper、torch、图片类视频和其他非三农流程依赖。FFmpeg 只收集 `ffmpeg.exe` 与 `ffprobe.exe`，不复制其文档目录。发布目录显式包含 `vcruntime140.dll`、`vcruntime140_1.dll`、`msvcp140.dll` 和 `ucrtbase.dll`，不依赖目标电脑预装 VC++ Redistributable。

选择 onedir 而非当前约 524 MB 的 onefile 模式，是为了减少启动解压时间、避免临时目录运行库冲突，并允许账号配置和资源独立更新。

## 测试与验收

按测试驱动方式实现，先添加失败测试再迁移生产代码。

单元测试覆盖：

- 标题仓储查询固定使用类型 6；
- 数据库无记录和数据库错误返回不同结果；
- 多账号公平轮询，并在全部耗尽后退出；
- 标题级失败被记录后继续；
- 连续 3 次系统级失败停止；
- 成功后标记标题并创建上传任务；
- 标签素材优先、随机素材兜底及素材去重；
- 配置相对路径解析和发布副本路径重写。

集成与回归验证覆盖：

- 现有 `tests/test_generation_regressions.py`；
- 新增三农服务测试；
- Python 语法编译；
- PyInstaller 构建成功；
- 对生成的 exe 运行 `--check`；
- 在隔离测试目录中验证 exe 不依赖原项目当前工作目录；
- 从包含中文和空格的可写路径启动 exe；
- 清空测试进程 PATH 后仍使用随包 FFmpeg；
- 分析发布目录，确认不存在 PyQt6、Qt6 或 ICU 运行库依赖；
- 校验 VC++ runtime 与 Python 运行库均随包存在；
- 原主程序能够导入并启动到类型 6 共享调用边界。

验收产物为 `dist_sanong/三农视频生成/` 完整目录，而不是只有无法脱离依赖运行的裸 exe。

## 非目标

- 不重写其他 12 种视频生成流程。
- 不新增完整桌面设置界面。
- 不更改现有数据库结构、标题字段含义或素材筛选规则。
- 不自动执行 FTP 上传。
- 不删除或覆盖原主程序及现有发布包。
- 不支持 Windows 7、32 位 Windows、Windows ARM、macOS 或 Linux。
- 不保证在无法访问数据库、AI、语音或素材服务的离线电脑上完成视频生成。
