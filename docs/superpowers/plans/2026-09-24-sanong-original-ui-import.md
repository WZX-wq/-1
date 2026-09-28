# 三农独立版原版界面与标题导入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用原版页面替换当前独立版界面，并在页面内提供可直接使用的三农标题 Excel 导入。

**Architecture:** 复用 `ui.new_batch_ai_autocut.Ui_new_batch_ai_autocut` 作为原版视觉外壳，继续通过 `GenerationWorker` 调用共享生成服务。新增纯 Excel 解析函数和仓储批量写入接口，GUI 使用独立 `TitleImportWorker` 串联二者。

**Tech Stack:** Python 3.12、PyQt6、openpyxl、mysql-connector、PyInstaller、unittest

**Spec:** `docs/superpowers/specs/2026-09-24-sanong-original-ui-import-design.md`

## Global Constraints

- 只导入和生成 `title_type = 6`。
- Excel 有无表头均可，空白过滤，文件内重复项去重且保持顺序。
- 启动后自动生成，标题耗尽后窗口不关闭。
- 复用原版 UI 文件，不复制完整主程序业务算法。
- 发布范围保持 Windows 10/11 x64 与 Windows Server 2016/2019/2022 x64。
- 仓库没有 Git，不执行 commit、分支或 worktree 步骤。

---

### Task 1: Excel 解析与数据库批量导入

**Files:**
- Create: `sanong_generation/title_import.py`
- Modify: `sanong_generation/repository.py`
- Create: `tests/test_sanong_title_import.py`
- Modify: `tests/test_sanong_repository.py`

**Interfaces:**
- Produces: `read_title_workbook(path: Path) -> list[str]`
- Produces: `SanongTitleRepository.import_titles(account_name: str, titles: Sequence[str]) -> TitleImportSummary`
- Produces: `TitleImportSummary(read: int, inserted: int, duplicates: int)`

- [x] **Step 1: 写无表头、有表头、空白和重复标题的失败测试**
- [x] **Step 2: 运行标题导入测试并确认因模块或接口缺失失败**
- [x] **Step 3: 实现只读 Excel 第一列解析与稳定去重**
- [x] **Step 4: 写固定账号、固定类型 6、提交与回滚的仓储失败测试**
- [x] **Step 5: 实现参数化批量写入和导入统计**
- [x] **Step 6: 重跑标题解析与仓储测试并确认通过**

### Task 2: 原版页面与后台导入线程

**Files:**
- Modify: `sanong_gui.py`
- Modify: `tests/test_sanong_gui.py`

**Interfaces:**
- Preserves: `SanongMainWindow(runtime, auto_start=True)`、`GenerationWorker`
- Produces: `TitleImportWorker(repository, account_name, workbook_path)`
- Produces: `SanongMainWindow.import_selected_titles()`

- [x] **Step 1: 更新 UI 测试，要求原版标题栏、标题文件区、三农类型和生产视频页**
- [x] **Step 2: 写无文件、无账号、导入成功和导入期间互斥的失败测试**
- [x] **Step 3: 运行 UI 测试并确认当前自定义页面不满足原版控件契约**
- [x] **Step 4: 用原版 UI 外壳重建窗口并绑定标题导入**
- [x] **Step 5: 映射生成状态、统计、日志、停止、目录按钮和延迟关闭**
- [x] **Step 6: 重跑 offscreen UI 测试并确认通过**
- [x] **Step 7: 用 Windows Qt 平台保存截图并与原版参照检查**

### Task 3: 原版资源打包与发布验收

**Files:**
- Modify: `build_sanong.ps1`
- Modify: `tests/test_sanong_packaging.py`
- Modify: `三农视频生成使用说明.txt`

**Interfaces:**
- Produces: 带原版页面和 `soft_pic` 的 `dist_sanong/三农视频生成/三农视频生成.exe`

- [x] **Step 1: 更新发布测试，要求 `soft_pic/4.png` 和 `soft_pic/cylogo.png`**
- [x] **Step 2: 更新构建脚本复制原版图标资源和使用说明**
- [x] **Step 3: 运行完整源码回归**
- [x] **Step 4: 重新构建并运行全部发布测试**
- [x] **Step 5: 在中文空格目录、空 `PATH` 下运行 `--check`**
- [x] **Step 6: 启动真实 EXE，验证原版窗口、自动耗尽后常驻和正常关闭**
- [x] **Step 7: 记录最终体积、SHA256 和截图**
