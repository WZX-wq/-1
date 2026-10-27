# Material Tag Fallback and AI Tag Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent valid local/remote materials from being marked missing solely because the first generated keyword is overly specific, and keep malformed AI tag values from aborting label workbook generation.

**Architecture:** Preserve the existing database and offline query filters. Query tag candidates in priority order until one has matches, then use that candidate pool for the existing remaining-tag intersection. Align the offline `中国` location behavior with the database query. Normalize AI tag arrays at the worker boundary before joining or writing them.

**Tech Stack:** Python, PyQt6 worker classes, unittest, openpyxl.

---

### Task 1: Regression coverage for offline location and tag fallback

**Files:**
- Modify: `tests/test_generation_regressions.py`
- Test: `database_tool/video_load_tool.py`

**Steps:**
1. Add an offline index test where `location='中国'` still accepts a cached material whose city is a specific city.
2. Add a query-fallback test where the first keyword returns no material and the next keyword returns a match; verify the successful keyword index and that no unrelated filters are removed.
3. Run those targeted tests and confirm they fail before implementation.

### Task 2: Implement bounded material keyword fallback

**Files:**
- Modify: `database_tool/video_load_tool.py`
- Modify: `main.py`

**Steps:**
1. Treat an empty or `中国` location as unrestricted in offline filtering, matching the database query.
2. Add a helper that tries supplied tags in order and returns the first non-empty candidate set and its tag index.
3. Update material-composition paths to seed candidate IDs from the first successful tag, then intersect only later tags. Preserve existing category, screen, duration, location, and allowed-ID constraints; do not add random unmatched fallback.
4. Run the targeted regression tests.

### Task 3: Normalize AI-produced tag values

**Files:**
- Modify: `worker/ai_worker.py`
- Modify: `tests/test_generation_regressions.py`

**Steps:**
1. Add one normalizer for list/tuple/set/string/dict responses; extract common `tag`, `keyword`, `name`, or `value` fields from dictionary entries and discard empty or unsupported values.
2. Apply normalization before all tag-list joins in worker flows.
3. Add a worker test with mixed string and dictionary labels, and assert the label workbook output is still written without an error signal.
4. Run generation-regression tests and the relevant worker test suite.

### Task 4: Release verification

**Files:**
- Modify: `version.json`
- Build: existing full-version PyInstaller release configuration

**Steps:**
1. Bump the application version to 2.4.15 if the repository release workflow supports a complete portable build in this environment.
2. Run the full relevant Python tests and `git diff --check`.
3. If building is supported, create a new portable package without overwriting the existing 2.4.14 ZIP; verify required directories and ZIP CRC.
4. Report any build or repository publication limitation explicitly.
