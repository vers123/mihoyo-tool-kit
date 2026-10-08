"""分类日志系统。

三类日志（对应原项目设计）：

* ``logs/console.log`` —— 终端全部输出（stdout/stderr + print + StreamHandler）
* ``logs/gui.log``     —— GUI 底部日志面板的消息，带时间戳
* ``logs/app.log``     —— ``logging`` 模块的结构化日志

``setup_console_log()`` 用 :class:`_TeeStream` 将 stdout/stderr 同时写终端与文件；
``setup_logger()`` 返回 ``app.log`` 的 logger；
``append_gui_log()`` 供 GUI 面板调用。
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Callable
from contextlib import suppress
from functools import wraps
from pathlib import Path
from typing import Any, TextIO, TypeVar

from ..core.paths import get_path_manager

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_TS_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

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


def setup_console_log() -> None:
    """将 stdout/stderr 镜像到 ``logs/console.log``（幂等）。"""
    if getattr(sys, "_mihoyo_console_configured", False):
        return
    log_file = _logs_dir() / "console.log"
    mirror = log_file.open("a", encoding="utf-8", buffering=1)
    sys.stdout = _TeeStream(_LiveStdout(sys.stdout, use_stderr=False), mirror)
    sys.stderr = _TeeStream(_LiveStdout(sys.stderr, use_stderr=True), mirror)
    sys._mihoyo_console_configured = True  # type: ignore[attr-defined]


def setup_logger(name: str = "mihoyo_toolkit", level: int = logging.INFO) -> logging.Logger:
    """配置并返回写入 ``logs/app.log`` 的 logger。"""
    global _configured
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers or not _configured:
        fmt = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
        file_handler = logging.FileHandler(_logs_dir() / "app.log", encoding="utf-8")
        file_handler.setFormatter(fmt)

        stream_handler = logging.StreamHandler(_LiveStdout(sys.stderr, use_stderr=True))
        stream_handler.setFormatter(fmt)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.propagate = False
        _configured = True
    return logger


def get_module_logger(name: str) -> logging.Logger:
    """获取子模块 logger（继承根配置）。"""
    return setup_logger(f"mihoyo_toolkit.{name}")


def append_gui_log(message: str) -> None:
    """将一条消息写入 ``logs/gui.log``（自动补时间戳，避免重复）。"""
    from datetime import datetime

    text = message.rstrip("\n")
    if not _TS_PREFIX.match(text):
        text = f"{datetime.now().strftime(_DATE_FORMAT)} {text}"
    with (_logs_dir() / "gui.log").open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")


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

    * ``app.log`` 被本包 logger 的 ``logging.FileHandler`` 持有；
    * ``console.log`` 被 :class:`_TeeStream` 的镜像文件对象持有。

    释放后会把 ``_configured`` 与 ``sys._mihoyo_console_configured`` 复位，使后续
    调用（``setup_logger()`` / ``setup_console_log()``）能重新创建日志文件；
    ``sys.stdout`` / ``sys.stderr`` 会还原为真实终端流，保证继续打印不受影响。
    """
    global _configured

    released = 0

    # 1) app.log：关闭并移除本包 logger 的文件处理器
    for name in list(logging.Logger.manager.loggerDict):
        if not name.startswith("mihoyo_toolkit"):
            continue
        target = logging.getLogger(name)
        for handler in list(target.handlers):
            if isinstance(handler, logging.FileHandler):
                with suppress(Exception):
                    handler.close()
                target.removeHandler(handler)
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
    "append_gui_log",
    "get_module_logger",
    "log_function_call",
    "setup_console_log",
    "setup_logger",
]
