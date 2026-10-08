"""自定义 GUI 组件"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from PySide6.QtWidgets import QPlainTextEdit, QProgressBar, QLabel, QWidget, QVBoxLayout


class LogViewer(QPlainTextEdit):
    """日志查看器组件 - 自动滚动、颜色高亮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)

    def append_log(self, message: str):
        """添加一条日志"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        lower = message.lower()
        if "[error]" in lower or "[fail" in lower:
            fmt.setForeground(QColor("#dc2626"))
            fmt.setFontWeight(QFont.Bold)
        elif "[warn" in lower:
            fmt.setForeground(QColor("#d97706"))
        elif "[ok]" in lower or "[success" in lower or "完成" in message:
            fmt.setForeground(QColor("#059669"))
        elif "[start]" in lower or "[info]" in lower:
            fmt.setForeground(QColor("#2563eb"))
        else:
            fmt.setForeground(QColor("#374151"))

        cursor.setCharFormat(fmt)
        cursor.insertText(message + "\n")

        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class ProgressWidget(QWidget):
    """进度组件 - 进度条 + 文字标签"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)

        self.label = QLabel("就绪")

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.label)

    def start(self, total: int = 0, text: str = ""):
        """开始进度"""
        self.progress_bar.setVisible(True)
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setRange(0, 0)
        if text:
            self.label.setText(text)

    def update_progress(self, current: int, total: int = 0, text: str = ""):
        """更新进度"""
        if total > 0:
            self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        if text:
            self.label.setText(text)
        elif total > 0:
            pct = int(current * 100 / total) if total > 0 else 0
            self.label.setText(f"{current}/{total} ({pct}%)")

    def finish(self, text: str = "就绪"):
        """完成进度"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QTimer.singleShot(1500, lambda: self.progress_bar.setVisible(False))
        self.label.setText(text)

    def reset(self, text: str = "就绪"):
        """重置进度"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.label.setText(text)
