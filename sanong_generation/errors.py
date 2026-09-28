class StartupConfigurationError(RuntimeError):
    """The portable runtime layout or configuration is invalid."""


class DatabaseWriteError(RuntimeError):
    """A required database state change did not complete."""


class TitleGenerationError(RuntimeError):
    """One title could not be generated and may be skipped."""


class MediaGenerationError(TitleGenerationError):
    """Audio or video processing failed for one title."""


class SystemGenerationError(RuntimeError):
    """Generation stopped after repeated system-level failures."""


class MemoryExhaustionError(SystemGenerationError):
    """Generation cannot continue because the system cannot allocate memory."""


_MEMORY_ERROR_MARKERS = (
    "cannot allocate memory",
    "not enough memory",
    "not enough memory resources",
    "insufficient memory",
    "out of memory",
    "memory allocation failed",
    "paging file is too small",
    "not enough storage is available to process this command",
    "内存不足",
    "内存分配失败",
    "无法分配内存",
    "页面文件太小",
    "分页文件太小",
)


MEMORY_EXHAUSTION_MESSAGE = (
    "内存不足：系统无法为视频处理分配所需内存，任务已停止，当前标题未标记成功。"
    "请关闭其他程序或增加 Windows 虚拟内存后重新运行。"
)


def is_memory_exhaustion(error: BaseException) -> bool:
    """Recognize Python, Windows page-file, and native-tool memory failures."""
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, MemoryError):
            return True
        if getattr(current, "winerror", None) == 1455 or getattr(
            current, "errno", None
        ) in (12, 1455):
            return True

        details = [str(current)]
        details.extend(
            str(value)
            for name in ("stderr", "stdout", "output")
            if (value := getattr(current, name, None))
        )
        message = " ".join(details).casefold()
        if any(marker in message for marker in _MEMORY_ERROR_MARKERS):
            return True

        for nested in (current.__cause__, current.__context__):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False


class InsufficientDiskSpaceError(SystemGenerationError):
    """Generation cannot safely continue because the target drive is full."""
