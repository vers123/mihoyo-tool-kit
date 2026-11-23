"""分类日志系统。

三类日志：

* ``logs/console.log`` —— 终端全部输出（stdout/stderr + print + StreamHandler）
* ``logs/gui.log``     —— GUI 底部日志面板的消息，带时间戳（按体积滚动）
* ``logs/app.log``     —— ``logging`` 模块的结构化日志（轮转保留）

关键约定：

* handler **只装在包级根 logger** ``mihoyo_toolkit`` 上一次（重复装会出现重复行、
  多份文件句柄，Windows 上还会导致日志文件被占用、清理时删不掉）；
* 子模块 logger 只设级别、依赖 ``propagate`` 向上汇总；
* 级别与轮转参数来自 ``[logging]`` 配置（缺省 INFO / 5 MiB / 3 份）。
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Callable
from contextlib import suppress
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, TextIO, TypeVar

from ..core.paths import get_path_manager

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_TS_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

#: 包级根 logger 名称（所有模块 logger 都挂在它下面）
ROOT_LOGGER_NAME = "mihoyo_toolkit"

#: 轮转默认值（配置不可用时回退）
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3

F = TypeVar("F", bound=Callable[..., Any])

_configured = False


class _LiveStdout:
    """始终写入「当前真实」终端流（``sys.__stdout__`` / ``sys.__stderr__``）。

    避免两个陷阱：

    1. 若直接写入 ``sys.stdout``，而 ``sys.stdout`` 已被 :class:`_TeeStream`
       替换，会造成无限递归；
    2. worker 线程销毁后写入已关闭的流会抛
       ``Signal source has been deleted``（``RuntimeError``）。
    """

    def __init__(self, fallback: TextIO, *, use_stderr: bool = False) -> None:
        self._fallback = fallback
        self._use_stderr = use_stderr

    def _target(self) -> TextIO:
        real = sys.__stderr__ if self._use_stderr else sys.__stdout__
        return real or self._fallback

    def write(self, data: str) -> int:
        try:
            return self._target().write(data)
        except (ValueError, RuntimeError):  # pragma: no cover - 关闭中的流
            return len(data)

    def flush(self) -> None:
        with suppress(ValueError, RuntimeError):  # pragma: no cover - 关闭中的流
            self._target().flush()

    def isatty(self) -> bool:
        try:
            return self._target().isatty()
        except (ValueError, RuntimeError):  # pragma: no cover
            return False

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - 透传
        return getattr(self._target(), name)


class _TeeStream:
    """将写入同时转发到终端与文件。"""

    def __init__(self, primary: Any, mirror: TextIO) -> None:
        self._primary = primary
        self._mirror = mirror

    def write(self, data: str) -> int:
        written = self._primary.write(data)
        try:
            self._mirror.write(data)
            self._mirror.flush()
        except (ValueError, RuntimeError):  # pragma: no cover
            pass
        return written

    def flush(self) -> None:
        self._primary.flush()
        with suppress(ValueError, RuntimeError):  # pragma: no cover - 镜像写入失败可忽略
            self._mirror.flush()

    def isatty(self) -> bool:
        try:
            return self._primary.isatty()
        except (ValueError, RuntimeError):  # pragma: no cover
            return False


def _logs_dir() -> Path:
    path = get_path_manager().logs
    path.mkdir(parents=True, exist_ok=True)
    return path


def _logging_settings() -> tuple[int, int, int]:
    """从配置读取 ``(级别, 单文件上限, 备份份数)``；读取失败时用默认值。"""
    try:
        from ..core.config import get_settings

        settings = get_settings().logging
        level = logging.getLevelName(settings.level.strip().upper())
        if not isinstance(level, int):
            level = logging.INFO
        return level, max(settings.max_bytes, 0), max(settings.backup_count, 0)
    except Exception:  # pragma: no cover - 配置不可用不应中断日志
        return logging.INFO, DEFAULT_MAX_BYTES, DEFAULT_BACKUP_COUNT


def setup_console_log() -> None:
    """将 stdout/stderr 镜像到 ``logs/console.log``（幂等）。"""
    if getattr(sys, "_mihoyo_console_configured", False):
        return
    log_file = _logs_dir() / "console.log"
    mirror = log_file.open("a", encoding="utf-8", buffering=1)
    sys.stdout = _TeeStream(_LiveStdout(sys.stdout, use_stderr=False), mirror)
    sys.stderr = _TeeStream(_LiveStdout(sys.stderr, use_stderr=True), mirror)
    sys._mihoyo_console_configured = True  # type: ignore[attr-defined]


def _build_handlers(level: int, max_bytes: int, backup_count: int) -> list[logging.Handler]:
    """构造包级根 logger 的 handler（文件 + 终端各一个）。"""
    fmt = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        _logs_dir() / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler(_LiveStdout(sys.stderr, use_stderr=True))
    stream_handler.setFormatter(fmt)
    return [file_handler, stream_handler]


def setup_logger(name: str = ROOT_LOGGER_NAME, level: int | None = None) -> logging.Logger:
    """配置并返回包级 logger（幂等：handler 只装一次）。

    Args:
        name: logger 名称；默认包级根 logger，子模块应传 ``mihoyo_toolkit.<模块>``。
        level: 该 logger 的显式级别；``None`` 表示沿用 ``[logging].level``。

    Returns:
        对应的 logger；子模块 logger 通过 ``propagate`` 汇总到根 logger 落盘。
    """
    global _configured

    root = logging.getLogger(ROOT_LOGGER_NAME)
    configured_level, max_bytes, backup_count = _logging_settings()

    if not _configured:
        # 重复配置会叠加 handler，产生重复行与多份文件句柄
        for handler in list(root.handlers):
            root.removeHandler(handler)
            with suppress(Exception):
                handler.close()
        for handler in _build_handlers(configured_level, max_bytes, backup_count):
            root.addHandler(handler)
        root.setLevel(configured_level)
        root.propagate = False
        _configured = True

    logger = root if name == ROOT_LOGGER_NAME else logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


def get_module_logger(name: str) -> logging.Logger:
    """获取子模块 logger（继承根 logger 的 handler，不重复落盘）。"""
    return setup_logger(f"{ROOT_LOGGER_NAME}.{name}")


def append_gui_log(message: str) -> None:
    """将一条消息写入 ``logs/gui.log``（自动补时间戳，避免重复）。

    文件超过 ``[logging].max_bytes`` 时滚动为 ``gui.log.1``（只保留一份）。
    """
    from datetime import datetime

    text = message.rstrip("\n")
    if not _TS_PREFIX.match(text):
        text = f"{datetime.now().strftime(_DATE_FORMAT)} {text}"

    path = _logs_dir() / "gui.log"
    _rotate_gui_log(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")


def _rotate_gui_log(path: Path) -> None:
    """``gui.log`` 超过上限时滚动（保留一份历史）。"""
    max_bytes = _logging_settings()[1]
    if max_bytes <= 0:
        return
    try:
        if path.is_file() and path.stat().st_size >= max_bytes:
            backup = path.with_name(f"{path.name}.1")
            with suppress(OSError):
                backup.unlink()
            path.replace(backup)
    except OSError:  # pragma: no cover - 文件被占用时继续写原文件
        pass


def log_function_call(func: F) -> F:

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_module_logger(func.__module__.split(".")[-1])
        logger.debug("调用 %s", func.__qualname__)
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            logger.error("%s 执行失败: %s", func.__qualname__, exc, exc_info=True)
            raise
        logger.debug("%s 完成", func.__qualname__)
        return result

    return wrapper  # type: ignore[return-value]


def _release_log_handles() -> int:
    """关闭 ``app.log`` / ``console.log`` 的文件句柄，返回释放数量。

    Windows 下无法删除被占用的文件，因此清理日志前必须先释放句柄：

    * ``app.log`` 被包级根 logger 的 ``RotatingFileHandler`` 持有；
    * ``console.log`` 被 :class:`_TeeStream` 的镜像文件对象持有。

    释放后会把 ``_configured`` 与 ``sys._mihoyo_console_configured`` 复位，使后续
    调用（``setup_logger()`` / ``setup_console_log()``）能重新创建日志文件；
    ``sys.stdout`` / ``sys.stderr`` 会还原为真实终端流，保证继续打印不受影响。
    """
    global _configured

    released = 0

    # 1) app.log：关闭并移除包级根 logger 的文件处理器。
    #    同时兜底扫描 ``mihoyo_toolkit.*`` —— 测试或第三方可能给子 logger 挂过
    #    FileHandler，句柄不释放同样会导致 Windows 删除失败。
    candidates = [logging.getLogger(ROOT_LOGGER_NAME)]
    candidates.extend(
        logging.getLogger(name)
        for name in list(logging.Logger.manager.loggerDict)
        if name.startswith(ROOT_LOGGER_NAME) and name != ROOT_LOGGER_NAME
    )
    for logger in candidates:
        for handler in list(logger.handlers):
            if not isinstance(handler, logging.FileHandler):
                continue
            logger.removeHandler(handler)
            with suppress(Exception):
                handler.close()
            released += 1
    _configured = False

    # 2) console.log：还原真实终端流并关闭镜像文件
    for attr in ("stdout", "stderr"):
        stream = getattr(sys, attr)
        if isinstance(stream, _TeeStream):
            setattr(sys, attr, stream._primary)
            with suppress(Exception):
                stream._mirror.close()
            released += 1
    if getattr(sys, "_mihoyo_console_configured", False):
        sys._mihoyo_console_configured = False  # type: ignore[attr-defined]

    return released


__all__ = [
    "DEFAULT_BACKUP_COUNT",
    "DEFAULT_MAX_BYTES",
    "ROOT_LOGGER_NAME",
    "append_gui_log",
    "get_module_logger",
    "log_function_call",
    "setup_console_log",
    "setup_logger",
]
