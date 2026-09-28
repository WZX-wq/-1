"""Console entry point for the portable three-agriculture generator."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Sequence

from database_tool.mysql_read_tool import DatabaseReadError
from database_tool.user_load_tool import add_user_task, get_account_by_name

from sanong_generation.config import (
    RunnerConfig,
    discover_accounts,
    validate_local_resources,
)
from sanong_generation.errors import (
    DatabaseWriteError,
    StartupConfigurationError,
    SystemGenerationError,
)
@dataclass(frozen=True)
class Runtime:
    config: RunnerConfig
    accounts: list[str]
    repository: Any
    service: Any
    log: logging.Logger


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _configure_logger(base_dir: Path) -> logging.Logger:
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sanong_runner")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_dir / "三农生成.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


def _configure_ffmpeg(config: RunnerConfig) -> None:
    current_path = os.environ.get("PATH", "")
    path_items = [str(config.ffmpeg_dir)]
    if current_path:
        path_items.append(current_path)
    os.environ["PATH"] = os.pathsep.join(path_items)
    os.environ["FFMPEG_BINARY"] = str(config.ffmpeg_dir / "ffmpeg.exe")
    os.environ["FFPROBE_BINARY"] = str(config.ffmpeg_dir / "ffprobe.exe")


def _validate_ffmpeg_runtime(config: RunnerConfig) -> None:
    for binary_name in ("ffmpeg.exe", "ffprobe.exe"):
        binary_path = config.ffmpeg_dir / binary_name
        try:
            result = subprocess.run(
                [str(binary_path), "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise StartupConfigurationError(
                f"无法运行随包 {binary_name}: {error}"
            ) from error
        if result.returncode != 0:
            raise StartupConfigurationError(
                f"随包 {binary_name} 自检失败，退出码 {result.returncode}"
            )


def _account_settings_loader(config: RunnerConfig):
    def load(account: str) -> dict:
        source = config.account_dir / f"{account}.txt"
        try:
            settings = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError("配置根节点不是 JSON 对象")
            shutil.copyfile(source, config.setting_path)
            return settings
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise StartupConfigurationError(
                f"账号 {account} 配置加载失败: {error}"
            ) from error

    return load


def _task_publisher(account_name: str, result) -> None:
    for account, mac in get_account_by_name(account_name) or []:
        task = {
            "name": account_name,
            "account": account,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": result.title,
            "mac": mac,
            "tag": result.tag,
            "path": str(result.video_path),
            "describe": ",".join(result.description),
            "classify": "旅游",
            "task_type": 6,
        }
        if not add_user_task(task):
            raise DatabaseWriteError(
                f"账号 {account_name}/{account} 创建上传任务失败"
            )


def build_runtime(base_dir: Path) -> Runtime:
    base_dir = Path(base_dir).resolve()
    os.chdir(base_dir)
    config = RunnerConfig.load(base_dir / "sanong_runner.json", base_dir)
    accounts = discover_accounts(config.account_dir)
    validate_local_resources(config, accounts)
    _configure_ffmpeg(config)
    _validate_ffmpeg_runtime(config)

    # Media modules import pydub, which probes PATH at import time. Load them
    # only after the bundled FFmpeg directory has been activated.
    from sanong_generation.composer import SanongComposer, SanongComposeOptions
    from sanong_generation.copywriter import generate_sanong_copywriting
    from sanong_generation.repository import SanongTitleRepository
    from sanong_generation.service import SanongGenerationService

    logger = _configure_logger(base_dir)
    repository = SanongTitleRepository()
    composer = SanongComposer(
        options=SanongComposeOptions(
            screen=config.screen,
            random_video_model=config.random_video_model,
        ),
        log=logger.info,
        base_dir=config.base_dir,
        music_dir=config.music_dir,
    )
    service = SanongGenerationService(
        config=config,
        repository=repository,
        copywriter=generate_sanong_copywriting,
        composer=composer,
        account_settings_loader=_account_settings_loader(config),
        task_publisher=_task_publisher,
        log=logger.info,
    )
    return Runtime(config, accounts, repository, service, logger)


def _bootstrap_error(message: str) -> None:
    try:
        logger = _configure_logger(executable_dir())
        logger.error(message)
    except Exception:
        print(message, file=sys.stderr)


def _parse_args(argv: Sequence[str] | None):
    parser = argparse.ArgumentParser(description="三农视频自动生成器")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查本地资源和数据库连接，不领取标题",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        runtime = build_runtime(executable_dir())
        runtime.repository.health_check()
        if args.check:
            runtime.log.info(
                "三农生成环境检查通过，发现 %d 个账号配置", len(runtime.accounts)
            )
            return 0
        runtime.log.info("开始自动生成三农视频，账号数: %d", len(runtime.accounts))
        summary = runtime.service.run(runtime.accounts)
        runtime.log.info(
            "生成结束: 成功 %d，标题失败 %d，已耗尽账号 %d/%d",
            summary.generated,
            summary.title_failures,
            summary.exhausted_accounts,
            summary.accounts,
        )
        return 0
    except StartupConfigurationError as error:
        _bootstrap_error(f"启动配置错误: {error}")
        return 2
    except (DatabaseReadError, DatabaseWriteError, SystemGenerationError) as error:
        _bootstrap_error(f"运行失败: {error}")
        return 1
    except Exception as error:
        _bootstrap_error(f"未处理的运行错误: {error}\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
