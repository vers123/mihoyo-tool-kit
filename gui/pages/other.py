"""其他抓取页面"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFormLayout
)
from gui.workers import ScraperWorker
from gui.widgets import ProgressWidget


class OtherPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(self._make_label("其他抓取"))
        layout.addWidget(self._make_label("角色图鉴、教程页面、图片提取、自定义抓取"))

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        self.btn_baike = QPushButton("抓取图鉴")
        self.btn_baike.clicked.connect(lambda: self._run_task("baike"))
        btn_row1.addWidget(self.btn_baike)

        self.btn_extract_images = QPushButton("提取图片")
        self.btn_extract_images.clicked.connect(lambda: self._run_task("images"))
        btn_row1.addWidget(self.btn_extract_images)
        btn_row1.addStretch()
        layout.addLayout(btn_row1)

        form = QFormLayout()
        form.setSpacing(8)

        self.tutorial_input = QLineEdit()
        self.tutorial_input.setPlaceholderText("mh4imrrhzdzi")
        self.tutorial_input.setText("mh4imrrhzdzi")
        form.addRow("教程ID:", self.tutorial_input)

        tutorial_btns = QHBoxLayout()
        self.btn_tutorial_fetch = QPushButton("抓取教程")
        self.btn_tutorial_fetch.clicked.connect(lambda: self._run_task("tutorial_fetch"))
        self.btn_tutorial_extract = QPushButton("提取角色")
        self.btn_tutorial_extract.clicked.connect(lambda: self._run_task("tutorial_extract"))
        tutorial_btns.addWidget(self.btn_tutorial_fetch)
        tutorial_btns.addWidget(self.btn_tutorial_extract)
        tutorial_btns.addStretch()
        form.addRow("", tutorial_btns)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        form.addRow("自定义URL:", self.url_input)

        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("custom_page.html")
        self.filename_input.setText("custom_page.html")
        form.addRow("输出文件名:", self.filename_input)

        self.btn_custom = QPushButton("自定义抓取")
        self.btn_custom.clicked.connect(lambda: self._run_task("custom"))
        form.addRow("", self.btn_custom)

        layout.addLayout(form)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self._stop_task)
        stop_layout = QHBoxLayout()
        stop_layout.addStretch()
        stop_layout.addWidget(self.btn_stop)
        layout.addLayout(stop_layout)

        self.progress = ProgressWidget()
        layout.addWidget(self.progress)
        layout.addStretch()

    def _make_label(self, text):
        lbl = QLabel(text)
        return lbl

    def _run_task(self, task):
        if self.worker and self.worker.isRunning():
            return

        func = None
        if task == "baike":
            from fetchers import run_baike
            func = run_baike
            self.progress.start(text="抓取角色图鉴中...")
        elif task == "images":
            from extractors import run_extract_images
            func = run_extract_images
            self.progress.start(text="提取图片链接中...")
        elif task == "tutorial_fetch":
            tid = self.tutorial_input.text().strip() or "mh4imrrhzdzi"
            from fetchers import run_tutorial
            func = lambda: run_tutorial(tid)
            self.progress.start(text=f"抓取教程 {tid} 中...")
        elif task == "tutorial_extract":
            tid = self.tutorial_input.text().strip() or "mh4imrrhzdzi"
            from extractors import run_extract_tutorial
            func = lambda: run_extract_tutorial(tid)
            self.progress.start(text=f"提取角色数据 {tid} 中...")
        elif task == "custom":
            url = self.url_input.text().strip()
            if not url:
                return
            filename = self.filename_input.text().strip() or "custom_page.html"
            from fetchers import run_custom
            func = lambda: run_custom(url, filename)
            self.progress.start(text=f"抓取 {url} 中...")

        if not func:
            return

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
        for btn in (self.btn_baike, self.btn_extract_images, self.btn_tutorial_fetch,
                     self.btn_tutorial_extract, self.btn_custom):
            btn.setEnabled(enabled)
