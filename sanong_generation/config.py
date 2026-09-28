from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import StartupConfigurationError


RUNTIME_DIRECTORIES = (
    "output",
    "cacheAFRVideo",
    "cacheCutVideo",
    "temp_title",
    "tempConcateVideo",
    "notSuccess",
    "logs",
)


def _resolve_path(base_dir: Path, value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _detect_ffmpeg_dir(base_dir: Path, configured: str | None) -> Path:
    if configured:
        return _resolve_path(base_dir, configured)

    candidates = (
        base_dir / "ffmpeg-bin",
        base_dir / "_internal" / "ffmpeg-bin",
        base_dir / "ffmpeg-7.1.1-essentials_build" / "bin",
    )
    return next((path for path in candidates if path.is_dir()), candidates[0])


@dataclass(frozen=True)
class RunnerConfig:
    base_dir: Path
    output_dir: Path
    ffmpeg_dir: Path
    screen: int
    random_video_model: bool
    create_upload_tasks: bool
    max_consecutive_system_failures: int
    minimum_free_space_mb: int = 1024

    @property
    def setting_path(self) -> Path:
        return self.base_dir / "setting.txt"

    @property
    def account_dir(self) -> Path:
        return self.base_dir / "video_model_set"

    @property
    def music_dir(self) -> Path:
        return self.base_dir / "cacheMusic1"

    @classmethod
    def load(cls, path: Path, base_dir: Path) -> "RunnerConfig":
        base_dir = Path(base_dir).resolve()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StartupConfigurationError(f"无法读取运行配置 {path}: {error}") from error
        if not isinstance(data, dict):
            raise StartupConfigurationError("运行配置必须是 JSON 对象")

        try:
            screen = int(data["screen"])
            failure_limit = int(data["max_consecutive_system_failures"])
            minimum_free_space_mb = int(data.get("minimum_free_space_mb", 1024))
            output_dir = _resolve_path(base_dir, data["output_dir"])
            random_model = bool(data["random_video_model"])
            create_tasks = bool(data["create_upload_tasks"])
        except (KeyError, TypeError, ValueError) as error:
            raise StartupConfigurationError(f"运行配置字段无效: {error}") from error

        if screen not in (0, 1):
            raise StartupConfigurationError("screen 只能是 0（竖屏）或 1（横屏）")
        if failure_limit < 1:
            raise StartupConfigurationError("max_consecutive_system_failures 必须大于 0")
        if minimum_free_space_mb < 128:
            raise StartupConfigurationError("minimum_free_space_mb 不能小于 128")

        return cls(
            base_dir=base_dir,
            output_dir=output_dir,
            ffmpeg_dir=_detect_ffmpeg_dir(base_dir, data.get("ffmpeg_dir")),
            screen=screen,
            random_video_model=random_model,
            create_upload_tasks=create_tasks,
            max_consecutive_system_failures=failure_limit,
            minimum_free_space_mb=minimum_free_space_mb,
        )


def discover_accounts(config_dir: Path) -> list[str]:
    config_dir = Path(config_dir)
    if not config_dir.is_dir():
        return []
    return sorted(path.stem for path in config_dir.glob("*.txt") if path.is_file())


def _validate_json_object(path: Path, label: str) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StartupConfigurationError(f"{label}无效: {path}: {error}") from error
    if not isinstance(value, dict):
        raise StartupConfigurationError(f"{label}必须是 JSON 对象: {path}")


def validate_local_resources(config: RunnerConfig, accounts: list[str]) -> None:
    if not config.setting_path.is_file():
        raise StartupConfigurationError(f"缺少默认配置: {config.setting_path}")
    _validate_json_object(config.setting_path, "默认配置")

    if not accounts:
        raise StartupConfigurationError(f"没有账号配置: {config.account_dir}")
    for account in accounts:
        _validate_json_object(config.account_dir / f"{account}.txt", "账号配置")

    music_files = (
        [path for path in config.music_dir.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"]
        if config.music_dir.is_dir()
        else []
    )
    if not music_files:
        raise StartupConfigurationError(f"缺少背景音乐: {config.music_dir}")

    for binary_name in ("ffmpeg.exe", "ffprobe.exe"):
        binary_path = config.ffmpeg_dir / binary_name
        if not binary_path.is_file():
            raise StartupConfigurationError(f"缺少 {binary_name}: {binary_path}")

    for directory_name in RUNTIME_DIRECTORIES:
        directory = config.output_dir if directory_name == "output" else config.base_dir / directory_name
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".sanong-write-check"
            probe.write_text("ok", encoding="ascii")
            probe.unlink()
        except OSError as error:
            raise StartupConfigurationError(f"目录不可写: {directory}: {error}") from error
