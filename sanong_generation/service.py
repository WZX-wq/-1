"""Round-robin service that generates type-6 videos until every account is empty."""

from __future__ import annotations

import errno
import shutil
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Callable, Sequence

from openpyxl import Workbook

from database_tool.mysql_read_tool import DatabaseReadError

from .composer import SanongVideoResult
from .copywriter import CopywritingFiles
from .errors import (
    InsufficientDiskSpaceError,
    MEMORY_EXHAUSTION_MESSAGE,
    MemoryExhaustionError,
    SystemGenerationError,
    TitleGenerationError,
    is_memory_exhaustion,
)
from .repository import SanongTitle


@dataclass(frozen=True)
class RunSummary:
    accounts: int
    generated: int
    title_failures: int
    exhausted_accounts: int


@dataclass
class _MutableRunSummary:
    accounts: int
    generated: int = 0
    title_failures: int = 0
    exhausted_accounts: int = 0

    def freeze(self) -> RunSummary:
        return RunSummary(
            self.accounts,
            self.generated,
            self.title_failures,
            self.exhausted_accounts,
        )


def _write_row(path: Path, values: Sequence[str]) -> Path:
    workbook = Workbook()
    workbook.active.append(list(values))
    workbook.save(path)
    return path


def _write_title_input(path: Path, title: str) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet["B1"] = "标题"
    sheet["B2"] = title
    workbook.save(path)
    return path


class SanongGenerationService:
    def __init__(
        self,
        *,
        config,
        repository,
        copywriter: Callable,
        composer,
        account_settings_loader: Callable[[str], dict],
        task_publisher: Callable[[str, SanongVideoResult], None],
        log: Callable[[str], None],
    ):
        self.config = config
        self.repository = repository
        self.copywriter = copywriter
        self.composer = composer
        self.account_settings_loader = account_settings_loader
        self.task_publisher = task_publisher
        self.log = log
        self._stop_requested = Event()

    def request_stop(self) -> None:
        self._stop_requested.set()

    def _copy_files(self, title: SanongTitle, account: str) -> CopywritingFiles:
        base_dir = Path(getattr(self.config, "base_dir", self.config.output_dir.parent))
        work_dir = base_dir / "temp_title" / f"sanong_{title.id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        copy_file = work_dir / "title_copy.xlsx"
        label_file = work_dir / "title_label.xlsx"

        if title.content and title.label:
            return CopywritingFiles(
                _write_row(copy_file, str(title.content).split("&&")),
                _write_row(label_file, str(title.label).split("&&")),
            )

        title_file = _write_title_input(work_dir / "title.xlsx", title.title)
        files = self.copywriter(title_file, account, title.id, self.log)
        if not isinstance(files, CopywritingFiles):
            try:
                return CopywritingFiles(Path(files.copy_file), Path(files.label_file))
            except (AttributeError, TypeError) as error:
                raise TitleGenerationError("三农文案生成没有返回有效文件") from error
        return files

    def _generate_one(self, account: str, title: SanongTitle) -> list[SanongVideoResult]:
        base_dir = Path(getattr(self.config, "base_dir", self.config.output_dir.parent))
        work_dir = base_dir / "temp_title" / f"sanong_{title.id}"
        try:
            settings = self.account_settings_loader(account)
            files = self._copy_files(title, account)
            output_dir = (
                Path(self.config.output_dir)
                / account
                / datetime.now().strftime("%Y%m%d")
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            results = self.composer.compose(
                files.copy_file,
                files.label_file,
                output_dir,
                account,
                settings,
            )
            if not results:
                raise TitleGenerationError(f"标题 {title.id} 没有生成视频")
            if self.config.create_upload_tasks:
                for result in results:
                    self.task_publisher(account, result)
            return results
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _ensure_free_space(self) -> None:
        minimum_mb = int(getattr(self.config, "minimum_free_space_mb", 0))
        if minimum_mb <= 0:
            return

        minimum_bytes = minimum_mb * 1024 * 1024
        base_dir = Path(getattr(self.config, "base_dir", self.config.output_dir.parent))
        write_locations = dict.fromkeys(
            (Path(self.config.output_dir), base_dir / "tempConcateVideo")
        )
        for location in write_locations:
            try:
                free_bytes = shutil.disk_usage(location).free
            except OSError as error:
                raise SystemGenerationError(
                    f"无法检查生成目录所在磁盘空间: {location}: {error}"
                ) from error
            if free_bytes < minimum_bytes:
                free_mb = free_bytes // (1024 * 1024)
                message = (
                    f"磁盘空间不足：{location} 所在磁盘仅剩 {free_mb} MB，"
                    f"至少需要 {minimum_mb} MB。请清理磁盘后重新运行。"
                )
                self.log(message)
                raise InsufficientDiskSpaceError(message)

    @staticmethod
    def _is_no_space_error(error: BaseException) -> bool:
        pending = [error]
        seen: set[int] = set()
        while pending:
            current = pending.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            if isinstance(current, OSError) and current.errno == errno.ENOSPC:
                return True
            message = str(current)
            if "No space left on device" in message or "磁盘空间不足" in message:
                return True
            for nested in (current.__cause__, current.__context__):
                if isinstance(nested, BaseException):
                    pending.append(nested)
        return False

    def run(
        self,
        accounts: Sequence[str],
        allowed_titles: Sequence[str] | None = None,
    ) -> RunSummary:
        self._stop_requested.clear()
        active = deque(dict.fromkeys(accounts))
        summary = _MutableRunSummary(accounts=len(active))
        consecutive_system_failures = 0

        while active:
            if self._stop_requested.is_set():
                self.log("已收到停止请求，不再领取新的三农标题")
                break
            self._ensure_free_space()
            account = active.popleft()
            try:
                title = self.repository.fetch_next(account, allowed_titles)
            except DatabaseReadError as error:
                consecutive_system_failures += 1
                self.log(
                    f"读取账号 {account} 的三农标题失败 "
                    f"({consecutive_system_failures}/"
                    f"{self.config.max_consecutive_system_failures}): {error}"
                )
                if consecutive_system_failures >= self.config.max_consecutive_system_failures:
                    raise SystemGenerationError(
                        f"连续 {consecutive_system_failures} 次读取标题失败: {error}"
                    ) from error
                active.append(account)
                continue

            if title is None:
                consecutive_system_failures = 0
                summary.exhausted_accounts += 1
                self.log(f"账号 {account} 已没有可用的三农标题")
                continue

            active.append(account)
            try:
                self._generate_one(account, title)
            except TitleGenerationError as error:
                if is_memory_exhaustion(error):
                    raise MemoryExhaustionError(MEMORY_EXHAUSTION_MESSAGE) from error
                self.repository.record_failure(title)
                summary.title_failures += 1
                consecutive_system_failures = 0
                self.log(f"标题 {title.id} 生成失败，继续下一个: {error}")
            except Exception as error:
                if is_memory_exhaustion(error):
                    raise MemoryExhaustionError(MEMORY_EXHAUSTION_MESSAGE) from error
                if self._is_no_space_error(error):
                    message = f"磁盘空间不足，生成已暂停: {error}"
                    self.log(message)
                    raise InsufficientDiskSpaceError(message) from error
                consecutive_system_failures += 1
                self.log(
                    f"标题 {title.id} 遇到系统错误 "
                    f"({consecutive_system_failures}/"
                    f"{self.config.max_consecutive_system_failures}): {error}"
                )
                if consecutive_system_failures >= self.config.max_consecutive_system_failures:
                    raise SystemGenerationError(
                        f"连续 {consecutive_system_failures} 次系统错误: {error}"
                    ) from error
            else:
                self.repository.mark_generated(title)
                summary.generated += 1
                consecutive_system_failures = 0
                self.log(f"标题 {title.id} 生成完成")

        return summary.freeze()
