from __future__ import annotations

from collections.abc import Iterable


MEMORY_EXHAUSTION_MESSAGE = (
    "内存不足：系统无法为视频处理分配所需内存，任务已停止，当前标题未标记成功。"
    "请关闭其他程序或增加 Windows 虚拟内存后重新运行。"
)

_MEMORY_ERROR_MARKERS = (
    "cannot allocate memory",
    "not enough memory",
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

_SYSTEM_ERROR_MARKERS = (
    "invalidendpoint",
    "closedendpoint",
    "endpoint unavailable",
    "api error",
    "api request",
    "connectionerror",
    "connection refused",
    "connection reset",
    "connection aborted",
    "network",
    "timeout",
    "timed out",
    "http 429",
    "http 500",
    "http 502",
    "http 503",
    "service unavailable",
    "temporarily unavailable",
    "api key",
    "authentication",
    "unauthorized",
    "未配置 ai",
    "接口密钥",
    "接口不可用",
    "网络错误",
    "请求超时",
    "服务不可用",
)


def _exception_chain(error: BaseException) -> Iterable[BaseException]:
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        for nested in (current.__cause__, current.__context__):
            if isinstance(nested, BaseException):
                pending.append(nested)


def is_memory_exhaustion(error: object) -> bool:
    """Recognize Python, Windows page-file, and native-tool memory failures."""
    if isinstance(error, BaseException):
        for current in _exception_chain(error):
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
            text = " ".join(details).casefold()
            if any(marker in text for marker in _MEMORY_ERROR_MARKERS):
                return True
        return False
    return any(marker in str(error).casefold() for marker in _MEMORY_ERROR_MARKERS)


def is_system_generation_error(error: object) -> bool:
    """Return whether an error is retryable infrastructure/API failure."""
    if is_memory_exhaustion(error):
        return True
    if isinstance(error, BaseException):
        text = " ".join(str(current) for current in _exception_chain(error))
    else:
        text = str(error)
    text = text.casefold()
    return any(marker in text for marker in _SYSTEM_ERROR_MARKERS)


__all__ = [
    "MEMORY_EXHAUSTION_MESSAGE",
    "is_memory_exhaustion",
    "is_system_generation_error",
]
