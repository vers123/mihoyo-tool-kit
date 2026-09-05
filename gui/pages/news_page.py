"""新闻页面基类 - 四款站点共用"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Qt
from gui.workers import ScraperWorker
from gui.widgets import ProgressWidget


class NewsPage(QWidget):
    """新闻页面基类"""

    game_key = ""
    game_name = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel(f"{self.game_name}新闻")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("抓取新闻页面 HTML，提取结构化数据")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_fetch = QPushButton("全量抓取")
        self.btn_fetch.setObjectName("primaryBtn")
        self.btn_fetch.clicked.connect(lambda: self._run_task("fetch", incremental=False))

        self.btn_incremental = QPushButton("增量抓取")
        self.btn_incremental.clicked.connect(lambda: self._run_task("fetch", incremental=True))

        self.btn_extract = QPushButton("提取数据")
        self.btn_extract.clicked.connect(lambda: self._run_task("extract", incremental=False))

        self.btn_incremental_extract = QPushButton("增量提取")
        self.btn_incremental_extract.clicked.connect(lambda: self._run_task("extract", incremental=True))

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self._stop_task)

        for btn in (self.btn_fetch, self.btn_incremental, self.btn_extract, self.btn_incremental_extract):
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        layout.addStretch()

    def _get_func(self, action: str, incremental: bool):
        """子类覆盖：返回要调用的函数"""
        raise NotImplementedError

    def _run_task(self, action: str, incremental: bool):
        if self.worker and self.worker.isRunning():
            return

        func = self._get_func(action, incremental)
        if func is None:
            return

        mode = "增量" if incremental else "全量"
        action_text = "抓取" if action == "fetch" else "提取"
        self.progress.start(text=f"{mode}{action_text}{self.game_name}新闻中...")

        self._set_buttons_enabled(False)
        self.btn_stop.setVisible(True)

        self.worker = ScraperWorker(func)
        main_window = self.window()
        if hasattr(main_window, 'log_viewer'):
            self.worker.log_message.connect(main_window.log_viewer.append_log)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.start()

    def _stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_interruption()
            self.btn_stop.setEnabled(False)

    def _on_finished(self, success: bool, message: str):
        self.progress.finish(message if success else f"失败: {message}")
        self._set_buttons_enabled(True)
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(True)
        if hasattr(self, 'worker') and self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _set_buttons_enabled(self, enabled: bool):
        for btn in (self.btn_fetch, self.btn_incremental, self.btn_extract, self.btn_incremental_extract):
            btn.setEnabled(enabled)
