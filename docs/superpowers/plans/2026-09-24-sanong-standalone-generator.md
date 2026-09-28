# 三农视频独立生成程序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提取标题类型 6 的三农视频生成逻辑，提供读取现有账号配置、运行到标题耗尽并可独立分发的 `三农视频生成.exe`。

**Architecture:** 新增无界面的 `sanong_generation` 包，将配置、标题仓储、文案生成、媒体合成和多账号调度从 QWidget 状态中解耦。原主程序的类型 6 分支与独立入口共同调用该包；PyInstaller 使用 onedir 发布并保留现有通用媒体工具。

**Tech Stack:** Python 3.12, unittest, pandas/openpyxl, mysql-connector-python, FFmpeg, PyInstaller 6.20；PyQt6 仅保留在原 GUI Worker 包装层，不进入独立程序

**Spec:** `docs/superpowers/specs/2026-09-24-sanong-standalone-generator-design.md`

## Global Constraints

- 独立入口只处理数据库 `title_type = 6`，不得进入其他视频类型。
- 所有账号都没有当天可用的三农标题时正常退出，不使用固定生成次数。
- 数据库故障必须与查询成功但无记录区分。
- 输出固定为发布目录下的 `output/<账号>/<YYYYMMDD>/`。
- 三农流程不校验或复制当前未使用的 `end_video_path`；其他视频类型行为不变。
- 成功后标记标题已生成，并按当前自动生成行为创建上传任务，但不执行 FTP 上传。
- 发布格式为 `dist_sanong/三农视频生成/三农视频生成.exe` 加 `_internal` 依赖目录。
- 支持 Windows 10/11 x64 和 Windows Server 2016/2019/2022 x64；不支持 Windows 7、32 位 Windows、Windows ARM、macOS 或 Linux。
- 目标电脑无需安装 Python、FFmpeg、Qt 或 VC++ Redistributable；发布目录必须位于用户可写路径，网络必须能访问现有外部服务。
- `sanong_runner.py` 的导入图不得包含 PyQt6、Qt6 或 ICU。
- 当前工作区没有 `.git`，不得擅自执行 `git init`；每个任务以测试结果和文件清单作为检查点，不执行 Git 提交。

---

### Task 1: 独立运行配置与目录校验

**Files:**
- Create: `sanong_generation/__init__.py`
- Create: `sanong_generation/errors.py`
- Create: `sanong_generation/config.py`
- Create: `sanong_runner.json`
- Create: `tests/test_sanong_config.py`

**Interfaces:**
- Consumes: JSON 运行配置、`video_model_set/*.txt`、`cacheMusic1/*.(mp3|MP3)`。
- Produces: `RunnerConfig.load(path: Path, base_dir: Path) -> RunnerConfig`、`discover_accounts(config_dir: Path) -> list[str]`、`validate_local_resources(config: RunnerConfig, accounts: list[str]) -> None`、`StartupConfigurationError`。

- [x] **Step 1: 写相对路径、账号发现和缺失资源的失败测试**

```python
class RunnerConfigTests(unittest.TestCase):
    def test_relative_output_is_resolved_from_executable_directory(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            config_path = base / "sanong_runner.json"
            config_path.write_text(json.dumps({
                "screen": 0,
                "random_video_model": True,
                "create_upload_tasks": True,
                "max_consecutive_system_failures": 3,
                "output_dir": "output",
            }), encoding="utf-8")
            config = RunnerConfig.load(config_path, base)
            self.assertEqual(config.output_dir, base / "output")

    def test_accounts_are_txt_stems_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "乙.txt").write_text("{}", encoding="utf-8")
            (directory / "甲.txt").write_text("{}", encoding="utf-8")
            self.assertEqual(discover_accounts(directory), ["乙", "甲"])

    def test_missing_background_music_is_a_startup_error(self):
        with self.assertRaisesRegex(StartupConfigurationError, "背景音乐"):
            validate_local_resources(config, ["测试账号"])
```

- [x] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_config -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'sanong_generation'`.

- [x] **Step 3: 实现配置模型、账号发现和本地校验**

```python
@dataclass(frozen=True)
class RunnerConfig:
    base_dir: Path
    output_dir: Path
    screen: int
    random_video_model: bool
    create_upload_tasks: bool
    max_consecutive_system_failures: int

    @classmethod
    def load(cls, path: Path, base_dir: Path) -> "RunnerConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        screen = int(data["screen"])
        if screen not in (0, 1):
            raise StartupConfigurationError("screen 只能是 0 或 1")
        failure_limit = int(data["max_consecutive_system_failures"])
        if failure_limit < 1:
            raise StartupConfigurationError("max_consecutive_system_failures 必须大于 0")
        output = Path(data["output_dir"])
        if not output.is_absolute():
            output = base_dir / output
        return cls(
            base_dir=base_dir,
            output_dir=output,
            screen=screen,
            random_video_model=bool(data["random_video_model"]),
            create_upload_tasks=bool(data["create_upload_tasks"]),
            max_consecutive_system_failures=failure_limit,
        )

def discover_accounts(config_dir: Path) -> list[str]:
    return sorted(path.stem for path in config_dir.glob("*.txt") if path.is_file())
```

`validate_local_resources` 必须验证 `setting.txt`、每个账号 JSON、至少一首背景音乐、`ffmpeg.exe`、`ffprobe.exe` 和输出/缓存目录可创建；不得读取或验证 `end_video_path`。

- [x] **Step 4: 运行配置测试并确认通过**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_config -v`

Expected: PASS，且没有网络访问。

- [x] **Step 5: 记录检查点**

Run: `Get-ChildItem sanong_generation,tests\test_sanong_config.py,sanong_runner.json -Recurse | Select-Object FullName,Length`

Expected: 新包、测试和默认配置均存在；工作区仍无 `.git`。

---

### Task 2: 可区分“耗尽”和“数据库失败”的标题仓储

**Files:**
- Modify: `database_tool/mysql_read_tool.py:12-44`
- Create: `sanong_generation/repository.py`
- Create: `tests/test_sanong_repository.py`

**Interfaces:**
- Consumes: `fetch_with_retry(..., raise_on_failure: bool = False)`、现有 `mark_title_generated`、`record_unsuccess_title_info`。
- Produces: `DatabaseReadError`、`DatabaseWriteError`、`SanongTitle`、`SanongTitleRepository.fetch_next(account_name: str) -> SanongTitle | None`、`health_check() -> None`、`mark_generated(title: SanongTitle) -> None`、`record_failure(title: SanongTitle) -> None`。

- [x] **Step 1: 写数据库错误与空结果分流的失败测试**

```python
class SanongTitleRepositoryTests(unittest.TestCase):
    def test_fetch_next_returns_none_only_for_successful_empty_query(self):
        with patch("sanong_generation.repository.fetch_with_retry", return_value=None) as query:
            repo = SanongTitleRepository()
            self.assertIsNone(repo.fetch_next("账号A"))
        sql, params = query.call_args.args[1:3]
        self.assertIn("title_type = %s", sql)
        self.assertEqual(params[0:2], ("账号A", 6))
        self.assertTrue(query.call_args.kwargs["raise_on_failure"])

    def test_fetch_next_propagates_database_read_error(self):
        with patch("sanong_generation.repository.fetch_with_retry",
                   side_effect=DatabaseReadError("数据库离线")):
            with self.assertRaises(DatabaseReadError):
                SanongTitleRepository().fetch_next("账号A")

    def test_fetch_with_retry_can_raise_after_retries(self):
        with patch.object(mysql_read_tool.mysql.connector, "connect",
                          side_effect=mysql.connector.Error("down")):
            with self.assertRaises(DatabaseReadError):
                mysql_read_tool.fetch_with_retry({}, "SELECT 1", raise_on_failure=True)
```

- [x] **Step 2: 运行测试并确认接口尚不存在**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_repository -v`

Expected: FAIL because `DatabaseReadError` or `SanongTitleRepository` is missing.

- [x] **Step 3: 为只读查询增加向后兼容的失败抛出选项**

```python
class DatabaseReadError(RuntimeError):
    pass

def fetch_with_retry(connect_kwargs, query, params=(), *, dictionary=False,
                     fetch_all=False, operation_name="数据库查询",
                     raise_on_failure=False):
    # 保留原有三次连接、执行和关闭逻辑。
    # 任一次成功时原样返回 fetchone/fetchall，包括成功查询的 None/[]。
    # 三次 mysql.connector.Error 后：
    if raise_on_failure:
        raise DatabaseReadError(f"{operation_name}失败: {last_error}")
    return None
```

默认值必须保持 `False`，不改变现有调用方。

- [x] **Step 4: 实现类型 6 仓储和明确的写入失败**

```python
@dataclass(frozen=True)
class SanongTitle:
    raw: tuple

    @property
    def id(self) -> int:
        return int(self.raw[0])

    @property
    def title(self) -> str:
        return str(self.raw[1])

    @property
    def content(self) -> str | None:
        return self.raw[2]

    @property
    def label(self) -> str | None:
        return self.raw[3]

class SanongTitleRepository:
    TITLE_TYPE = 6

    def fetch_next(self, account_name: str) -> SanongTitle | None:
        row = fetch_with_retry(
            TITLE_DB_CONFIG,
            SANONG_TITLE_QUERY,
            (account_name, self.TITLE_TYPE, today_pattern()),
            operation_name="获取三农标题",
            raise_on_failure=True,
        )
        return SanongTitle(row) if row is not None else None
```

`mark_generated` 和 `record_failure` 在底层函数返回非真值时抛出 `DatabaseWriteError`。`health_check` 使用 `SELECT 1` 和 `raise_on_failure=True`。

- [x] **Step 5: 运行仓储测试和现有数据库回归测试**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_repository tests.test_generation_regressions.SanongGenerationTests -v`

Expected: PASS，现有默认 `fetch_with_retry` 调用行为不变。

- [x] **Step 6: 记录检查点**

Run: `& '.build-python312-official\python.exe' -m py_compile database_tool\mysql_read_tool.py sanong_generation\repository.py`

Expected: exit code 0.

---

### Task 3: 提取三农文案与分段标签生成

**Files:**
- Create: `sanong_generation/copywriter.py`
- Modify: `worker/ai_worker.py:182-274`
- Modify: `tests/test_generation_regressions.py:252-325`
- Create: `tests/test_sanong_copywriter.py`

**Interfaces:**
- Consumes: `douBao_ai_strategy_content`、`deepseek_ai_strategy_topic`、`deepseek_ai_strategy_tag`、`segment_title`、`write_arrays_to_excel`、`update_video_title_info`。
- Produces: `CopywritingFiles(copy_file: Path, label_file: Path)`、`generate_sanong_copywriting(excel_file_path: Path, account_name: str, title_id: int = -1, progress: Callable[[str], None] | None = None) -> CopywritingFiles`；原 `AiDisposeMaterialStrategyTitle` 保留兼容包装。

- [x] **Step 1: 写服务函数产出和错误的失败测试**

```python
@contextmanager
def title_workbook(text):
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "titles.xlsx"
        workbook = Workbook()
        workbook.active["B2"] = text
        workbook.save(path)
        yield path

class SanongCopywriterTests(unittest.TestCase):
    def test_generates_copy_label_files_and_updates_database(self):
        with title_workbook("闲置土地如何利用") as title_file, \
             patch("sanong_generation.copywriter.douBao_ai_strategy_content",
                   return_value=["开场", "方法"]), \
             patch("sanong_generation.copywriter.deepseek_ai_strategy_topic",
                   return_value=["土地利用"]), \
             patch("sanong_generation.copywriter.deepseek_ai_strategy_tag",
                   side_effect=[["闲置土地"], ["农业政策"]]), \
             patch("sanong_generation.copywriter.segment_title", return_value="闲置土地如何利用"), \
             patch("sanong_generation.copywriter.update_video_title_info", return_value=True):
            result = generate_sanong_copywriting(title_file, "三农", 321)
        self.assertEqual(result.copy_file.name, "titles_copy.xlsx")
        self.assertEqual(result.label_file.name, "titles_label.xlsx")

    def test_empty_copywriting_raises_title_generation_error(self):
        with title_workbook("宅基地政策") as title_file, \
             patch("sanong_generation.copywriter.douBao_ai_strategy_content", return_value=[]):
            with self.assertRaisesRegex(TitleGenerationError, "文案生成失败"):
                generate_sanong_copywriting(title_file, "三农", 654)
```

- [x] **Step 2: 运行测试并确认服务函数尚不存在**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_copywriter -v`

Expected: FAIL because `sanong_generation.copywriter` is missing.

- [x] **Step 3: 把现有 Worker 主体提取为同步函数**

```python
@dataclass(frozen=True)
class CopywritingFiles:
    copy_file: Path
    label_file: Path

def generate_sanong_copywriting(excel_file_path, account_name, title_id=-1, progress=None):
    notify = progress or (lambda _message: None)
    # 保留现有三次文案重试、三次标签重试和本地标签兜底。
    # 先完整生成内存结果，再写 copy/label 两个文件。
    # title_id != -1 时数据库更新失败必须抛 TitleGenerationError。
    return CopywritingFiles(copy_path, label_path)
```

`AiDisposeMaterialStrategyTitle.run()` 只调用该函数，将 `progress` 映射到 `progressResultReady.emit`，成功发 `finished`，异常发 `errorOccurred`。不得保留第二份生成算法。

- [x] **Step 4: 更新旧测试 patch 目标并运行新旧测试**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_copywriter tests.test_generation_regressions.SanongGenerationTests -v`

Expected: PASS；旧 Worker 外部接口保持兼容。

- [x] **Step 5: 记录检查点**

Run: `rg -n "douBao_ai_strategy_content|deepseek_ai_strategy_tag" sanong_generation\copywriter.py worker\ai_worker.py`

Expected: 算法调用只存在于 `copywriter.py`，`ai_worker.py` 仅调用共享函数。

---

### Task 4: 提取无 Qt 的共享媒体核心

**Files:**
- Create: `sanong_generation/media_core.py`
- Create: `tests/test_sanong_media_core.py`
- Modify: `worker/sa_worker.py:1-45`
- Modify: `worker/composite_video_worker.py:1-260`
- Modify: `worker/add_music_worker.py:1-25`

**Interfaces:**
- Consumes: `produce_audio_and_subtitles_to_path`、`add_audio_and_subtitles_to_part`、`concatenate_videos_in_segments`、`addCover`、`add_bgm_to_video`。
- Produces: `AudioSubtitle(audio_path: Path, srt_path: Path)`、`generate_audio_subtitles(texts: Sequence[str], audio_settings: dict, output_dir: Path, progress: Callable[[str], None] | None = None) -> list[AudioSubtitle]`、`compose_video_segments(video_paths: Sequence[Path], audio_paths: Sequence[Path], ass_paths: Sequence[Path], title_ass_paths: Sequence[Path], output_path: Path, transition: dict, pic_time: float, max_workers: int = 4, progress: Callable[[int, int, str], None] | None = None) -> Path`、`add_background_music(video_path: Path, music_path: Path, video_volume: int, music_volume: int, output_path: Path) -> Path`。

- [x] **Step 1: 写核心函数不导入 Qt、异常直接抛出和返回真实路径的失败测试**

```python
class MediaCoreTests(unittest.TestCase):
    def test_module_does_not_import_pyqt(self):
        script = "import sys; import sanong_generation.media_core; " \
                 "assert not any(name.startswith('PyQt6') for name in sys.modules)"
        subprocess.run([sys.executable, "-c", script], check=True)

    def test_add_background_music_returns_existing_output(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "final.mp4"
            with patch("sanong_generation.media_core.add_bgm_to_video",
                       side_effect=lambda *_args: output.touch()):
                result = add_background_music(
                    Path("input.mp4"), Path("music.mp3"), 100, 40, output)
            self.assertEqual(result, output)

    def test_add_background_music_raises_when_output_is_missing(self):
        with tempfile.TemporaryDirectory() as root, \
             patch("sanong_generation.media_core.add_bgm_to_video", return_value=None):
            with self.assertRaisesRegex(MediaGenerationError, "背景音乐"):
                add_background_music(Path("input.mp4"), Path("music.mp3"), 100, 40,
                                     Path(root) / "missing.mp4")
```

- [x] **Step 2: 写 GUI Worker 只转发核心结果的失败测试**

```python
def test_add_music_worker_wraps_shared_core(self):
    worker = AddMusicWorker("in.mp4", "music.mp3", 100, 40, "out.mp4")
    finished, errors = [], []
    worker.signals.finished.connect(finished.append)
    worker.signals.errorOccurred.connect(errors.append)
    with patch("worker.add_music_worker.add_background_music", return_value=Path("out.mp4")):
        worker.run()
    self.assertEqual(finished, ["添加背景音乐完成"])
    self.assertEqual(errors, [])
```

为 `SaWorker` 和 `CompositeVideo` 各写同形测试：patch 共享核心，断言参数透传、成功信号一次；共享核心抛异常时只发一次 `errorOccurred`。

- [x] **Step 3: 运行测试并确认媒体核心尚不存在**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_media_core -v`

Expected: FAIL because `sanong_generation.media_core` is missing.

- [x] **Step 4: 从三个 Worker 提取普通同步函数**

```python
def add_background_music(video_path, music_path, video_volume, music_volume, output_path):
    output_path = Path(output_path)
    add_bgm_to_video(str(video_path), str(music_path), video_volume, music_volume,
                     str(output_path))
    if not output_path.is_file():
        raise MediaGenerationError(f"背景音乐处理后未生成文件: {output_path}")
    return output_path
```

`generate_audio_subtitles` 使用 `asyncio.run` 顺序调用现有语音函数，返回约定的 `temp_final_audio{index}.mp3` 和 `temp_subtitle{index}.srt` 路径并逐一验证存在。`compose_video_segments` 搬移 `CompositeVideo.run()` 中的并发片段处理、完整性检查、合并、封面和清理逻辑；任何片段失败都抛 `MediaGenerationError`，不得产出残缺视频。

- [x] **Step 5: 将 QRunnable 改为共享核心的薄包装**

```python
class AddMusicWorker(QRunnable):
    def run(self):
        try:
            add_background_music(self.video_path, self.music_path, self.video_volume,
                                 self.music_volume, self.output_file)
            self.signals.finished.emit("添加背景音乐完成")
        except Exception as error:
            self.signals.errorOccurred.emit(str(error))
```

`SaWorker` 和 `CompositeVideo` 采用同样结构并把 progress 回调映射到原有信号；不得在 Worker 中保留第二份媒体算法。

- [x] **Step 6: 运行媒体核心和现有视频回归测试**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_media_core tests.test_generation_regressions.VideoConcatFallbackTests tests.test_generation_regressions.CoverMergeTests -v`

Expected: PASS。

- [x] **Step 7: 记录检查点**

Run: `& '.build-python312-official\python.exe' -c "import sys; import sanong_generation.media_core; assert not any(n.startswith('PyQt6') for n in sys.modules)"`

Expected: exit code 0，媒体核心导入不加载 PyQt6。

---

### Task 5: 提取三农媒体合成器

**Files:**
- Create: `sanong_generation/composer.py`
- Create: `tests/test_sanong_composer.py`
- Modify: `main.py:6208-6647`

**Interfaces:**
- Consumes: `RunnerConfig` 中的屏幕方向和随机模板选项、账号设置字典、copy/label Excel、三农素材查询下载函数、现有 SaWorker/CompositeVideo/AddMusicWorker。
- Produces: `PreparedSegment(audio_path: Path, ass_path: Path, audio_length: float)`、`PreparedMaterial(material_id: int, video_path: Path)`、`SanongVideoResult(video_path: Path, title: str, tag: str, description: tuple[str, ...], material_ids: tuple[int, ...])`、`MediaBackend`、`SanongComposer.compose(copy_file: Path, label_file: Path, output_dir: Path, account_name: str, settings: dict) -> list[SanongVideoResult]`。

- [x] **Step 1: 写标签优先、随机兜底和缺素材失败测试**

```python
class SanongMaterialSelectionTests(unittest.TestCase):
    def test_first_available_tag_candidate_wins(self):
        selected = select_sanong_material(
            tags=["土地", "农业"], used_ids={8}, screen=0, audio_length=12,
            query_by_tag=lambda tag, *_: [{"id": 8}, {"id": 9}] if tag == "土地" else [],
            random_id=lambda _screen: 10,
            download=lambda material_id: Path(f"{material_id}.mp4"),
            exists=lambda path: path.name == "9.mp4",
        )
        self.assertEqual(selected.material_id, 9)

    def test_random_fallback_is_bounded(self):
        with self.assertRaisesRegex(TitleGenerationError, "20"):
            select_sanong_material(
                tags=[], used_ids=set(), screen=0, audio_length=12,
                query_by_tag=lambda *_: [], random_id=lambda _screen: None,
                download=lambda _id: Path("missing.mp4"), exists=lambda _path: False,
            )
```

- [x] **Step 2: 写合成器返回实际输出且不要求片尾的失败测试**

```python
def write_excel_row(path, values):
    workbook = Workbook()
    sheet = workbook.active
    for column, value in enumerate(values, start=1):
        sheet.cell(row=1, column=column, value=value)
    workbook.save(path)
    return path

class FakeMediaBackend:
    def prepare_segments(self, parts, audio_settings, settings, title, screen):
        return [
            PreparedSegment(Path(f"{index}.mp3"), Path(f"{index}.ass"), 8.0)
            for index, _part in enumerate(parts)
        ]

    def material_for_segment(self, tags, used_ids, screen, audio_length):
        material_id = len(used_ids) + 1
        return PreparedMaterial(material_id, Path(f"cut-{material_id}.mp4"))

    def render(self, segments, materials, intermediate_path, pic_time):
        intermediate_path.touch()
        return intermediate_path

    def add_music(self, intermediate_path, final_path):
        final_path.touch()
        return final_path

def test_compose_returns_actual_video_without_end_video_dependency(self):
    settings = {
        "voice_set": {"api_type": 0, "role_0": 0, "spd_0": 0, "vol_0": 100},
        "title_set": {},
        "srt_set": {},
    }
    settings["end_video"] = {"end_video_path": "Z:/missing.mp4"}
    with tempfile.TemporaryDirectory() as root:
        output_dir = Path(root) / "output"
        output_dir.mkdir()
        copy_file = write_excel_row(
            Path(root) / "copy.xlsx", ["测试标题", "三农", "片段1", "片段2", "片段3"])
        label_file = write_excel_row(
            Path(root) / "label.xlsx", ["标签1", "标签2", "标签3"])
        composer = SanongComposer(media=FakeMediaBackend(), log=lambda _message: None)
        results = composer.compose(copy_file, label_file, output_dir, "账号A", settings)
        self.assertEqual(results[0].video_path, output_dir / "测试标题.mp4")
```

测试文件中的 `write_excel_row` 使用 openpyxl 创建一行真实工作簿并返回路径，不 mock Excel 读取。`MediaBackend` 的生产实现负责把现有 worker 和 ffmpeg 工具适配为 `prepare_segments`、`material_for_segment`、`render`、`add_music` 四个窄接口。

- [x] **Step 3: 运行测试并确认合成器尚不存在**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_composer -v`

Expected: FAIL with missing composer interfaces.

- [x] **Step 4: 实现素材选择和显式音频配置构造**

```python
EDGE_ROLES = (
    "zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoxuanNeural",
    "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural", "zh-CN-YunxiaNeural",
    "zh-CN-YunyangNeural", "zh-CN-liaoning-XiaobeiNeural",
    "zh-CN-shaanxi-XiaoniNeural",
)
BAIDU_ROLES = (
    1, 0, 3, 4, 5003, 5118, 106, 5, 4003, 4106, 4115, 5147, 5976,
    5971, 4164, 4176, 4259, 4119, 4105, 4117, 4288, 4192, 4100, 4103,
    4144, 4278, 4143, 4140, 4129, 4149, 4254, 4206, 4147, 4141, 4226,
    4179, 4146, 6567, 4156, 4189, 4194, 4193, 4195, 4196, 4197,
)

def build_audio_settings(settings: dict) -> dict:
    voice = settings["voice_set"]
    if voice["api_type"] == 0:
        speed = str(voice["spd_0"])
        return {"api_type": 0, "audio_role": EDGE_ROLES[voice["role_0"]],
                "speed_value": (speed if speed.startswith("-") else "+" + speed) + "%",
                "volume_value": voice["vol_0"]}
    return {"api_type": 1, "audio_role": BAIDU_ROLES[voice["role_1"]],
            "speed_value": voice["spd_1"], "volume_value": voice["vol_1"],
            "tone_value": voice["pit_1"]}
```

`select_sanong_material` 按标签顺序查询，跳过已用 ID，标签无结果后最多随机尝试 20 次；无法得到本地可读素材时抛 `TitleGenerationError`。

- [x] **Step 5: 把 `compositeMaterialStrategyVideo` 主体迁移到 `SanongComposer`**

```python
class SanongComposer:
    def compose(self, copy_file, label_file, output_dir, account_name, settings):
        # 读取每行标题、总标签、文案和逐段标签。
        # media.generate_audio_subtitles(video_text, audio_setting, temp_dir) 生成音频/字幕。
        # 为每段创建 ASS，调用 select_sanong_material 并按音频长度裁剪。
        # media.compose_video_segments(part_videos, part_audio, part_ass, title_ass,
        #                              intermediate_path,
        #                              {"transitionNum": 0, "transitionTime": 0}, pic_time) 拼接。
        # 从 cacheMusic1 随机选音乐，调用
        # media.add_background_music(intermediate_path, music_path, 100, 40, final_path)。
        # 写 video_id.xlsx 和 1.xls，删除中间 _0.mp4。
        # 每个成功行追加 SanongVideoResult；不足三段或素材不足抛 TitleGenerationError。
        return results
```

保留现有字幕、标题样式、背景音乐音量 40、视频音量 100、无转场和素材去重行为。删除类型 6 的 `end_video_path` 存在性检查及所有 QMessageBox/QApplication 调用。

- [x] **Step 6: 将主程序原方法缩减为共享合成器适配**

```python
def compositeMaterialStrategyVideo(self, copy_file, out_dir_path, account_name, label_file=None):
    options = SanongComposeOptions(
        screen=self.screenComboBox.currentIndex(),
        random_video_model=self.randomVideoModelCheckBox.isChecked(),
    )
    composer = SanongComposer(options=options, log=self.add_log)
    return composer.compose(Path(copy_file), Path(label_file), Path(out_dir_path),
                            account_name, read_dict_from_txt("setting.txt"))
```

- [x] **Step 7: 运行合成器和现有三农回归测试**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_composer tests.test_generation_regressions.SanongGenerationTests -v`

Expected: PASS；测试证明缺失片尾不会阻断类型 6。

- [x] **Step 8: 检查三农算法不存在重复副本**

Run: `rg -n "正在按标签匹配三农素材|匹配素材超过20次" main.py sanong_generation`

Expected: 算法日志只出现在 `sanong_generation/composer.py`，`main.py` 只有调用边界。

---

### Task 6: 多账号运行到耗尽的服务

**Files:**
- Create: `sanong_generation/service.py`
- Create: `tests/test_sanong_service.py`

**Interfaces:**
- Consumes: `RunnerConfig`、账号名列表、`SanongTitleRepository`、`generate_sanong_copywriting`、`SanongComposer`、现有 `get_account_by_name`/`add_user_task`。
- Produces: `RunSummary(accounts: int, generated: int, title_failures: int, exhausted_accounts: int)`、`SanongGenerationService.run(accounts: Sequence[str]) -> RunSummary`。

- [x] **Step 1: 写公平轮询和全部耗尽终止的失败测试**

```python
def title(title_id):
    return SanongTitle((
        title_id, f"标题{title_id}",
        f"标题{title_id}&&三农&&片段1&&片段2&&片段3",
        "标签1&&标签2&&标签3", None, "账号", 6, None, 0,
    ))

def success(title_id):
    return [SanongVideoResult(
        video_path=Path(f"标题{title_id}.mp4"),
        title=f"标题{title_id}", tag="三农",
        description=("片段1", "片段2", "片段3"), material_ids=(1, 2, 3),
    )]

class FakeRepository:
    def __init__(self, queues=None, fetch_error=None):
        self.queues = {name: deque(items) for name, items in (queues or {}).items()}
        self.fetch_error = fetch_error
        self.fetch_order = []
        self.failed_ids = []
        self.generated_ids = []
        self.fetch_count = 0

    def fetch_next(self, account):
        self.fetch_count += 1
        self.fetch_order.append(account)
        if self.fetch_error:
            raise self.fetch_error
        return self.queues[account].popleft()

    def record_failure(self, item):
        self.failed_ids.append(item.id)

    def mark_generated(self, item):
        self.generated_ids.append(item.id)

def make_service(repository, compose_side_effect=None, failure_limit=3):
    config = SimpleNamespace(
        max_consecutive_system_failures=failure_limit,
        create_upload_tasks=False,
        output_dir=Path("output"),
    )
    composer = Mock()
    if compose_side_effect is None:
        composer.compose.return_value = success(1)
    else:
        composer.compose.side_effect = compose_side_effect
    return SanongGenerationService(
        config=config,
        repository=repository,
        copywriter=Mock(),
        composer=composer,
        account_settings_loader=lambda _account: {},
        task_publisher=lambda _account, _result: None,
        log=lambda _message: None,
    )

def test_round_robins_accounts_until_each_is_exhausted(self):
    repository = FakeRepository({
        "甲": [title(1), title(3), None],
        "乙": [title(2), None],
    })
    service = make_service(repository=repository)
    summary = service.run(["甲", "乙"])
    self.assertEqual(repository.fetch_order, ["甲", "乙", "甲", "乙", "甲"])
    self.assertEqual(summary.generated, 3)
    self.assertEqual(summary.exhausted_accounts, 2)
```

- [x] **Step 2: 写失败分类和连续系统失败阈值的失败测试**

```python
def test_title_failure_is_recorded_and_next_title_runs(self):
    repository = FakeRepository({"甲": [title(1), title(2), None]})
    service = make_service(repository=repository,
                           compose_side_effect=[TitleGenerationError("素材不足"), success(2)])
    summary = service.run(["甲"])
    self.assertEqual(repository.failed_ids, [1])
    self.assertEqual(summary.generated, 1)
    self.assertEqual(summary.title_failures, 1)

def test_three_consecutive_database_failures_abort(self):
    repository = FakeRepository(fetch_error=DatabaseReadError("down"))
    service = make_service(repository=repository, failure_limit=3)
    with self.assertRaises(SystemGenerationError):
        service.run(["甲", "乙"])
    self.assertEqual(repository.fetch_count, 3)
```

- [x] **Step 3: 运行测试并确认服务尚不存在**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_service -v`

Expected: FAIL with missing `SanongGenerationService`.

- [x] **Step 4: 实现活动账号队列和明确状态转换**

```python
def run(self, accounts):
    active = deque(accounts)
    summary = MutableRunSummary(accounts=len(accounts))
    consecutive_system_failures = 0
    while active:
        account = active.popleft()
        try:
            title = self.repository.fetch_next(account)
        except DatabaseReadError as error:
            consecutive_system_failures += 1
            if consecutive_system_failures >= self.config.max_consecutive_system_failures:
                raise SystemGenerationError(str(error)) from error
            active.append(account)
            continue
        if title is None:
            summary.exhausted_accounts += 1
            continue
        active.append(account)
        try:
            self._generate_one(account, title)
        except TitleGenerationError:
            self.repository.record_failure(title)
            summary.title_failures += 1
        else:
            self.repository.mark_generated(title)
            summary.generated += 1
        consecutive_system_failures = 0
    return summary.freeze()
```

`_generate_one` 先复制账号配置到运行时 `setting.txt`，复用已有 content/label 或调用 copywriter，再调用 composer。成功且 `create_upload_tasks` 为真时，为 `get_account_by_name(account)` 返回的每个账号调用 `add_user_task`，字段与现有类型 6 任务一致。

- [x] **Step 5: 运行服务测试**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_service -v`

Expected: PASS，循环会自然耗尽而非依赖生成次数。

- [x] **Step 6: 记录检查点**

Run: `& '.build-python312-official\python.exe' -m py_compile sanong_generation\service.py`

Expected: exit code 0.

---

### Task 7: 独立入口、自检和主程序共享调用

**Files:**
- Create: `sanong_runner.py`
- Create: `tests/test_sanong_runner.py`
- Modify: `main.py:1806-1835`
- Modify: `main.py:13643-13701`

**Interfaces:**
- Consumes: Tasks 1-6 的配置、仓储、合成器和服务。
- Produces: `sanong_runner.main(argv: Sequence[str] | None = None) -> int`；`--check` 返回 0/2；正常运行返回 0/1/2。

- [x] **Step 1: 写 `--check` 不领取标题和退出码测试**

```python
def test_check_validates_without_fetching_title(self):
    with patch("sanong_runner.build_runtime") as build_runtime:
        runtime = build_runtime.return_value
        runtime.accounts = ["账号A"]
        runtime.repository.health_check.return_value = None
        code = main(["--check"])
    self.assertEqual(code, 0)
    runtime.repository.fetch_next.assert_not_called()

def test_configuration_error_returns_two(self):
    with patch("sanong_runner.build_runtime",
               side_effect=StartupConfigurationError("缺少音乐")):
        self.assertEqual(main([]), 2)
```

- [x] **Step 2: 运行测试并确认入口尚不存在**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_runner -v`

Expected: FAIL because `sanong_runner` is missing.

- [x] **Step 3: 实现工作目录、日志、FFmpeg 和退出码**

```python
def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def main(argv=None):
    args = parse_args(argv)
    try:
        runtime = build_runtime(executable_dir())
        runtime.repository.health_check()
        if args.check:
            runtime.log.info("三农生成环境检查通过")
            return 0
        summary = runtime.service.run(runtime.accounts)
        runtime.log.info("生成结束: %s", summary)
        return 0
    except StartupConfigurationError as error:
        log_startup_error(error)
        return 2
    except (DatabaseReadError, DatabaseWriteError, SystemGenerationError) as error:
        log_runtime_error(error)
        return 1
```

日志同时使用 `StreamHandler` 和 `RotatingFileHandler(logs/三农生成.log)`。入口及其所有 `sanong_generation` 依赖不得导入任何 PyQt6 模块。

- [x] **Step 4: 把主程序类型 6 文案入口改为共享函数/兼容 Worker**

`main.py` 保留现有多类型账号轮询，但类型 6 的文案生成和合成必须调用 Task 3/5 的共享实现。主程序仍通过 UI 日志回调显示进度，其他分支不改。

- [x] **Step 5: 运行入口和主程序回归测试**

Run: `& '.build-python312-official\python.exe' -m unittest tests.test_sanong_runner tests.test_generation_regressions -v`

Expected: PASS。

- [x] **Step 6: 验证独立入口导入图不含 Qt**

Run: `& '.build-python312-official\python.exe' -c "import sys; import sanong_runner; assert not any(n.startswith('PyQt6') for n in sys.modules), sorted(n for n in sys.modules if n.startswith('PyQt6'))"`

Expected: exit code 0。

- [x] **Step 7: 运行完整语法编译**

Run: `& '.build-python312-official\python.exe' -m compileall -q sanong_generation sanong_runner.py main.py worker database_tool`

Expected: exit code 0，无语法错误。

- [x] **Step 8: 记录检查点**

Run: `rg -n "title_type = %s|SanongGenerationService|SanongComposer" sanong_generation sanong_runner.py main.py`

Expected: 独立服务固定类型 6，主程序和独立入口均引用共享实现。

---

### Task 8: PyInstaller 独立目录构建与验收

**Files:**
- Create: `sanong_runner.spec`
- Create: `build_sanong.ps1`
- Create: `tests/test_sanong_packaging.py`
- Modify: `tests/test_packaged_dependencies.py`

**Interfaces:**
- Consumes: `.build-python312-official`、Task 7 入口、当前 `setting.txt`、`video_model_set`、`cacheMusic1`、FFmpeg 两个可执行文件。
- Produces: `dist_sanong/三农视频生成/三农视频生成.exe` 和可移动运行目录。

- [x] **Step 1: 写 spec 结构和发布资源的失败测试**

```python
class SanongPackagingTests(unittest.TestCase):
    def test_release_directory_contains_mutable_runtime_resources(self):
        release = Path(os.environ["SANONG_RELEASE_DIR"])
        self.assertTrue((release / "三农视频生成.exe").is_file())
        self.assertTrue((release / "sanong_runner.json").is_file())
        self.assertTrue((release / "setting.txt").is_file())
        self.assertTrue(any((release / "video_model_set").glob("*.txt")))
        self.assertTrue(any((release / "cacheMusic1").glob("*.[mM][pP]3")))
        self.assertTrue((release / "_internal" / "ffmpeg-bin" / "ffmpeg.exe").is_file())
        self.assertTrue((release / "_internal" / "ffmpeg-bin" / "ffprobe.exe").is_file())

    def test_release_contains_windows_runtime_and_no_qt(self):
        release = Path(os.environ["SANONG_RELEASE_DIR"])
        names = {path.name.lower() for path in release.rglob("*") if path.is_file()}
        for required in ("vcruntime140.dll", "vcruntime140_1.dll",
                         "msvcp140.dll", "ucrtbase.dll", "python312.dll"):
            self.assertIn(required, names)
        forbidden = {name for name in names
                     if name.startswith(("pyqt6", "qt6", "icu"))}
        self.assertEqual(forbidden, set())
```

- [x] **Step 2: 运行测试并确认发布目录尚不存在**

Run: `$env:SANONG_RELEASE_DIR=(Resolve-Path '.').Path + '\dist_sanong\三农视频生成'; & '.build-python312-official\python.exe' -m unittest tests.test_sanong_packaging -v`

Expected: FAIL because `三农视频生成.exe` is absent.

- [x] **Step 3: 编写 onedir spec**

```python
runtime_dir = r"C:\Windows\System32"
runtime_names = (
    "msvcp140.dll", "ucrtbase.dll", "vcruntime140.dll", "vcruntime140_1.dll",
)
package_metadata = (
    copy_metadata("imageio")
    + copy_metadata("imageio-ffmpeg")
    + copy_metadata("moviepy")
)
a = Analysis(
    ["sanong_runner.py"],
    pathex=[".source-run-deps"],
    binaries=[
        *[(os.path.join(runtime_dir, name), ".") for name in runtime_names],
        (os.path.join(ffmpeg_bin_dir, "ffmpeg.exe"), "ffmpeg-bin"),
        (os.path.join(ffmpeg_bin_dir, "ffprobe.exe"), "ffmpeg-bin"),
    ],
    datas=package_metadata,
    hiddenimports=["xlrd"] + collect_submodules("mysql.connector"),
    excludes=["PyQt6", "whisper", "torch", "torchaudio", "torchvision",
              "transformers", "tensorflow", "matplotlib", "tkinter", "_tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="三农视频生成",
          console=True, icon=["tb.ico"], upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="三农视频生成")
```

不得从 `main.spec` 复制 Qt/ICU 设置。可编辑配置、账号和音乐不放进 `_internal`，由构建脚本在 COLLECT 后复制到发布目录顶层。构建前逐个验证 runtime 和 FFmpeg 源文件存在，缺失时立即失败。

- [x] **Step 4: 编写可重复构建脚本**

```powershell
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.build-python312-official\python.exe'
& $python -m PyInstaller --noconfirm --clean --distpath `
  (Join-Path $projectRoot 'dist_sanong') --workpath `
  (Join-Path $projectRoot 'build_sanong') (Join-Path $projectRoot 'sanong_runner.spec')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 构建失败' }
$release = Join-Path $projectRoot 'dist_sanong\三农视频生成'
Copy-Item -LiteralPath (Join-Path $projectRoot 'setting.txt') -Destination $release -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'sanong_runner.json') -Destination $release -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'video_model_set') -Destination $release -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'cacheMusic1') -Destination $release -Recurse -Force
```

脚本只覆盖 `dist_sanong/三农视频生成` 和 `build_sanong`，不修改源配置，不触碰现有 `dist*` 目录。

- [x] **Step 5: 构建发布目录**

Run: `& '.\build_sanong.ps1'`

Expected: exit code 0，生成 `dist_sanong/三农视频生成/三农视频生成.exe`。

- [x] **Step 6: 运行打包资源和运行库测试**

Run: `$env:SANONG_RELEASE_DIR=(Resolve-Path 'dist_sanong\三农视频生成').Path; $env:PACKAGED_EXE_PATH=Join-Path $env:SANONG_RELEASE_DIR '三农视频生成.exe'; & '.build-python312-official\python.exe' -m unittest tests.test_sanong_packaging tests.test_packaged_dependencies -v`

Expected: PASS，Python、MSVC/UCRT、FFmpeg 和可编辑资源均存在，且发布目录不含 PyQt6、Qt6 或 ICU 文件。

- [x] **Step 7: 在中文、空格和空 PATH 的隔离路径运行打包 exe 自检**

Run: `$source=(Resolve-Path 'dist_sanong\三农视频生成').Path; $isolated=Join-Path $env:TEMP ('三农 独立运行 ' + [guid]::NewGuid().ToString('N')); Copy-Item -LiteralPath $source -Destination $isolated -Recurse; $proc=Start-Process -FilePath (Join-Path $isolated '三农视频生成.exe') -ArgumentList '--check' -WorkingDirectory $env:TEMP -Environment @{PATH=''} -Wait -PassThru -NoNewWindow; if($proc.ExitCode -ne 0){ throw "--check failed: $($proc.ExitCode)" }`

Expected: exit code 0，`logs/三农生成.log` 出现在隔离发布目录而不是原项目或 `%TEMP%`，证明不依赖系统 Python、FFmpeg 或 PATH。

- [x] **Step 8: 运行完整回归套件**

Run: `& '.build-python312-official\python.exe' -m unittest discover -s tests -p 'test_*.py' -v`

Expected: 所有测试通过，0 failures，0 errors。

- [x] **Step 9: 核对最终产物和大小**

Run: `$release=Get-Item 'dist_sanong\三农视频生成'; $bytes=(Get-ChildItem $release.FullName -Recurse -File | Measure-Object Length -Sum).Sum; [pscustomobject]@{Exe=(Join-Path $release.FullName '三农视频生成.exe'); Files=(Get-ChildItem $release.FullName -Recurse -File).Count; SizeMB=[math]::Round($bytes/1MB,2)} | Format-List`

Expected: 顶层 exe、资源与 `_internal` 完整，目录可整体复制运行。

- [x] **Step 10: 生成兼容性报告**

Run: `& (Join-Path (Resolve-Path 'dist_sanong\三农视频生成').Path '三农视频生成.exe') --check > 'dist_sanong\三农视频生成\compatibility-report.txt' 2>&1; if($LASTEXITCODE -ne 0){ throw "compatibility check failed: $LASTEXITCODE" }; Get-Content -LiteralPath 'dist_sanong\三农视频生成\compatibility-report.txt'`

Expected: 报告包含 Windows 版本、x64 架构、可写目录、FFmpeg/ffprobe 版本、Python runtime、数据库连通性和外部服务检查结果；不输出数据库密码或 API 密钥。
