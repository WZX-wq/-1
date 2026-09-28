# 三农标题生成修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 `title_type=6` 三农流程，使其可靠生成并保存文案与标签，并优先按标签匹配三农视频素材。

**Architecture:** 保留现有三农专用 Worker 和合成函数，只补齐缺失的数据产物与匹配边界。Worker 为每个标题写入 `_copy.xlsx`、`_label.xlsx` 并回写 `video_title_info.content/label`；素材层新增限定 `material_application='三农素材'` 的标签查询；合成层先使用标签查询结果，查询不到时沿用随机三农素材兜底。AI 文案或标签完全失败时通过 Worker 错误信号中止当前标题，避免空文件进入合成。

**Tech Stack:** Python, PyQt6 QRunnable, pandas/openpyxl, MySQL Connector/Python, unittest.mock。

---

### Task 1: 覆盖三农 Worker 的文案标签产物

**Files:**
- Modify: `worker/ai_worker.py:182-238`
- Test: `tests/test_generation_regressions.py`

**Steps:**
1. 为 type 6 Worker 增加标签文件路径和逐段标签生成。
2. 对文案空返回、标签空返回增加有限重试和明确错误信号；正常结果写入两个 Excel，并调用 `update_video_title_info`。
3. 用 mock 验证文案、标签文件及数据库回写参数。

### Task 2: 增加三农标签素材查询

**Files:**
- Modify: `database_tool/video_load_tool.py`
- Modify: `main.py:40-48`
- Test: `tests/test_generation_regressions.py`

**Steps:**
1. 新增按首标签、屏幕方向和音频时长查询三农素材的函数，SQL 固定限定 `material_application='三农素材'` 及可用状态。
2. 保持现有随机三农查询不变，增加 mock 查询测试，确保参数和结果透传。

### Task 3: 让三农合成优先按标签匹配并处理 AI 失败

**Files:**
- Modify: `main.py:1804-1823`
- Modify: `main.py:6405-6429`
- Test: `tests/test_generation_regressions.py`

**Steps:**
1. type 6 自动生成在 Worker 报错后记录失败并跳过合成，避免读取不存在的文案文件。
2. 合成每个片段时按标签查询三农候选，下载并去重；无标签候选时保留随机三农素材兜底。
3. 运行定向单测、语法编译和现有回归测试，确认旅游流程未被改动。
