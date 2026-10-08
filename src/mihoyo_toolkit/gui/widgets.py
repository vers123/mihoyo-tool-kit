"""通用 GUI 组件：全局日志面板与进度组件。"""

from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QProgressBar, QVBoxLayout, QWidget

from ..utils import append_gui_log
from . import theme


class LogViewer(QPlainTextEdit):
    """日志面板：着色高亮 + 自动滚动 + 同步写入 ``logs/gui.log``。

    面板保留最近 :data:`~mihoyo_toolkit.gui.theme.LOG_MAX_BLOCKS` 条原始消息，
    以便系统主题切换后按新配色重绘。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(theme.LOG_MAX_BLOCKS)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._messages: list[str] = []

    def append_log(self, message: str) -> None:
        """追加一条日志。

        消息若已自带时间戳则不会重复添加（时间戳处理统一由
        :func:`~mihoyo_toolkit.utils.logger.append_gui_log` 负责）。
        """
        text = message.rstrip("\n")
        if not text:
            return

        with suppress(OSError):
            # 日志文件不可写不应影响界面
            append_gui_log(text)

        self._messages.append(text)
        if len(self._messages) > theme.LOG_MAX_BLOCKS:
            del self._messages[: len(self._messages) - theme.LOG_MAX_BLOCKS]

        self._render(text)

    def reapply_theme(self) -> None:
        """主题切换后按新配色重绘已有日志（不重复写入日志文件）。"""
        if not self._messages:
            return
        messages = list(self._messages)
        self.clear()
        for text in messages:
            self._render(text)

    def clear_log(self) -> None:
        """清空面板显示（不影响日志文件）。"""
        self._messages.clear()
        self.clear()

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #
    def _render(self, text: str) -> None:
        """按当前主题着色写入一行。"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(theme.log_color(text)))
        lower = text.lower()
        if "[error]" in lower or "[fail" in lower:
            fmt.setFontWeight(QFont.Weight.Bold)

        cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class ProgressWidget(QWidget):
    """进度组件：进度条 + 百分比 / 描述文字。

    * :meth:`start` 进入忙碌（不确定进度）状态；
    * :meth:`update_progress` / :meth:`set_percent` 显示确定进度与百分比；
    * :meth:`finish` / :meth:`reset` 结束并自动收起进度条。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._percent = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setVisible(False)

        self.label = QLabel("就绪")

        layout.addWidget(self.bar)
        layout.addWidget(self.label)

    # ------------------------------------------------------------------ #
    #  状态切换
    # ------------------------------------------------------------------ #
    def start(self, text: str = "处理中…", total: int = 0) -> None:
        """开始进度；``total`` 为 0 时显示忙碌动画。"""
        self.bar.setVisible(True)
        self.bar.setFormat("")
        if total > 0:
            self.bar.setRange(0, 100)
        else:
            self.bar.setRange(0, 0)
        self.bar.setValue(0)
        self._percent = 0
        self.label.setText(text)

    def update_progress(self, current: int, total: int = 0, text: str = "") -> None:
        """更新确定进度。"""
        if total > 0:
            self._percent = max(0, min(100, int(current * 100 / total)))
            self.bar.setRange(0, 100)
            self.bar.setValue(self._percent)
            self.bar.setFormat(f"{self._percent}%")
            if not text:
                text = f"{current}/{total}（{self._percent}%）"
        if text:
            self.label.setText(text)

    def set_percent(self, percent: int) -> None:
        """由 ``TaskWorker.progress(int)`` 信号驱动的百分比更新。"""
        self._percent = max(0, min(100, int(percent)))
        self.bar.setVisible(True)
        self.bar.setRange(0, 100)
        self.bar.setValue(self._percent)
        self.bar.setFormat(f"{self._percent}%")
        self.label.setText(f"进度 {self._percent}%")

    def finish(self, text: str = "任务完成") -> None:
        """标记完成并延时收起进度条。"""
        self.bar.setVisible(True)
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.bar.setFormat("100%")
        self._percent = 100
        self.label.setText(text)
        QTimer.singleShot(1500, self._hide_bar)

    def reset(self, text: str = "就绪") -> None:
        """重置为初始状态。"""
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat("")
        self.bar.setVisible(False)
        self._percent = 0
        self.label.setText(text)

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #
    def _hide_bar(self) -> None:
        self.bar.setVisible(False)


__all__ = ["LogViewer", "ProgressWidget"]
