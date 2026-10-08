"""QThread 异步任务 Worker。

GUI 线程只负责界面；抓取 / 提取 / 导出 / 过滤等耗时操作全部由
:class:`TaskWorker` 在后台线程执行，避免阻塞事件循环。

Worker 会重定向 ``sys.stdout`` / ``sys.stderr``，把任务内的 ``print`` 与
logger 输出按行实时转发为 Qt 信号（界面逐行刷新）。该重定向同时充当
**协作式取消点**：用户请求中断后，下一次写入即抛出 :class:`TaskCancelledError`
终止任务，因此无需修改 core 层代码。
"""

from __future__ import annotations

import io
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout, suppress
from typing import Any

from PySide6.QtCore import QThread, Signal

from ..core.exceptions import MihoyoError


class TaskCancelledError(Exception):
    """协作式取消：由输出流在检测到中断标志时抛出。"""


class _SignalStream(io.TextIOBase):
    """把写入内容按行转成 Qt 信号，并作为取消检查点。"""

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, emit: Callable[[str], None], is_cancelled: Callable[[], bool]) -> None:
        super().__init__()
        self._emit = emit
        self._is_cancelled = is_cancelled
        self._buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if self._is_cancelled():
            raise TaskCancelledError
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit_line(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            line, self._buffer = self._buffer, ""
            self._emit_line(line)

    def _emit_line(self, line: str) -> None:
        line = line.rstrip("\r")
        if not line.strip():
            return
        with suppress(RuntimeError):
            # 接收者（窗口 / 面板）已销毁，静默丢弃
            self._emit(line)


class TaskWorker(QThread):
    """在后台线程执行任意可调用对象的 Worker。

    Signals:
        progress: 百分比进度（0-100），由任务主动上报。
        message: 任务输出的一行日志。
        finished_ok: 任务正常结束，携带函数返回值。
        failed: 任务异常结束，携带错误描述。
        cancelled: 任务被用户中断。

    Note:
        完成信号命名为 ``finished_ok`` 而非 ``finished``，因为 ``QThread`` 已
        自带无参的 ``finished`` 信号，重名会导致基类信号被覆盖。
    """

    progress = Signal(int)
    message = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        func: Callable[..., Any],
        *args: Any,
        label: str = "任务",
        parent: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent)
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._label = label
        self._cancel_requested = False

    @property
    def label(self) -> str:
        """任务名称（用于日志）。"""
        return self._label

    def request_cancellation(self) -> None:
        """请求中断任务（协作式）。"""
        self._cancel_requested = True
        self.requestInterruption()

    def is_cancelled(self) -> bool:
        """是否已请求中断。"""
        return self._cancel_requested or self.isInterruptionRequested()

    def run(self) -> None:
        stream = _SignalStream(self.message.emit, self.is_cancelled)
        error_stream = _SignalStream(self.message.emit, self.is_cancelled)
        try:
            with redirect_stdout(stream), redirect_stderr(error_stream):
                result = self._func(*self._args, **self._kwargs)
        except TaskCancelledError:
            self._emit_cancelled()
            return
        except MihoyoError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:
            # 后台线程中的任何异常都不应让进程崩溃，转为 failure 信号
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return

        stream.flush()
        error_stream.flush()

        if self.is_cancelled():
            self._emit_cancelled()
            return
        self.finished_ok.emit(result)

    def _emit_cancelled(self) -> None:
        self.message.emit("[WARN] 任务已被用户中断")
        self.cancelled.emit()


__all__ = ["TaskCancelledError", "TaskWorker"]
