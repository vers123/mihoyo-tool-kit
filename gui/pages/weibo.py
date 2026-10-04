"""微博页面"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from gui.workers import ScraperWorker
from gui.widgets import ProgressWidget


class WeiboPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(self._make_label("微博"))
        layout.addWidget(self._make_label("抓取微博用户主页，提取数据"))

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_fetch = QPushButton("全量抓取")
        self.btn_fetch.clicked.connect(lambda: self._run_task("fetch", False))

        self.btn_incremental = QPushButton("增量抓取")
        self.btn_incremental.clicked.connect(lambda: self._run_task("fetch", True))

        self.btn_extract = QPushButton("提取数据")
        self.btn_extract.clicked.connect(lambda: self._run_task("extract", False))

        self.btn_incremental_extract = QPushButton("增量提取")
        self.btn_incremental_extract.clicked.connect(lambda: self._run_task("extract", True))

        self.btn_stop = QPushButton("停止")
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

    def _make_label(self, text):
        lbl = QLabel(text)
        return lbl

    def _get_func(self, action, incremental):
        if action == "fetch":
            from fetchers import run_weibo
            return lambda: run_weibo(incremental=incremental)
        else:
            from extractors import run_extract_weibo
            return lambda: run_extract_weibo(incremental=incremental)

    def _run_task(self, action, incremental):
        if self.worker and self.worker.isRunning():
            return
        func = self._get_func(action, incremental)
        if not func:
            return
        mode = "增量" if incremental else "全量"
        action_text = "抓取" if action == "fetch" else "提取"
        self.progress.start(text=f"{mode}{action_text}微博数据中...")
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

    def _on_finished(self, success, message):
        self.progress.finish(message if success else f"失败: {message}")
        self._set_buttons_enabled(True)
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(True)
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _set_buttons_enabled(self, enabled):
        for btn in (self.btn_fetch, self.btn_incremental, self.btn_extract, self.btn_incremental_extract):
            btn.setEnabled(enabled)
