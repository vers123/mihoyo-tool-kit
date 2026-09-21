"""TXT 过滤页面"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox, QCheckBox,
    QGroupBox, QAbstractItemView, QMessageBox
)
from PySide6.QtCore import Qt
from gui.workers import ScraperWorker
from gui.widgets import ProgressWidget
from extractors.txt_filter import TxtFilter, FIELD_CHOICES, MATCH_CHOICES, MATCH_EXACT, SORT_CHOICES, SORT_DESC
from gui.pages.preview_dialog import PreviewDialog


class FilterPage(QWidget):
    """TXT 文件过滤页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.txt_filter = TxtFilter()
        self._file_entries = []  # [(rel, abs, n), ...]
        self._setup_ui()
        self._refresh_files()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(self._make_label("TXT 文件过滤"))
        layout.addWidget(self._make_label(
            "按关键词匹配提取行，按时间升序/降序重新编号"
        ))

        # 文件列表
        files_group = QGroupBox("可用文件（可多选）")
        files_layout = QVBoxLayout(files_group)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.file_list.setMaximumHeight(180)
        files_layout.addWidget(self.file_list)

        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self._refresh_files)
        files_layout.addWidget(refresh_btn)
        layout.addWidget(files_group)

        # 关键词输入
        kw_group = QGroupBox("关键词与匹配设置")
        kw_layout = QVBoxLayout(kw_group)

        kw_row = QHBoxLayout()
        kw_row.addWidget(QLabel("关键词:"))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("多个关键词用空格分隔（OR 逻辑）")
        kw_row.addWidget(self.kw_input)
        kw_layout.addLayout(kw_row)

        field_row = QHBoxLayout()
        field_row.addWidget(QLabel("匹配字段:"))
        self.field_combo = QComboBox()
        for key, label in FIELD_CHOICES:
            self.field_combo.addItem(label, key)
        field_row.addWidget(self.field_combo)
        field_row.addStretch()
        kw_layout.addLayout(field_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("匹配模式:"))
        self.mode_combo = QComboBox()
        for key, label in MATCH_CHOICES:
            self.mode_combo.addItem(label, key)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        kw_layout.addLayout(mode_row)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("排序方向:"))
        self.sort_combo = QComboBox()
        for key, label in SORT_CHOICES:
            self.sort_combo.addItem(label, key)
        sort_row.addWidget(self.sort_combo)
        sort_row.addStretch()
        kw_layout.addLayout(sort_row)

        layout.addWidget(kw_group)

        # 执行按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_preview = QPushButton("预览")
        self.btn_preview.clicked.connect(self._preview)

        self.btn_run = QPushButton("执行过滤")
        self.btn_run.clicked.connect(self._run_filter)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self._stop_task)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_preview)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        # 进度
        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        layout.addStretch()

    def _make_label(self, text):
        lbl = QLabel(text)
        return lbl

    def _refresh_files(self):
        """刷新文件列表"""
        self.file_list.clear()
        self._file_entries = self.txt_filter.list_txt_files()
        for rel, ab, n in self._file_entries:
            item = QListWidgetItem(f"{rel}  ({n} 行)")
            item.setData(Qt.UserRole, ab)
            self.file_list.addItem(item)

    def _get_params(self):
        """获取选中的文件、关键词、字段、匹配模式、排序方向，校验不通过返回 None"""
        selected_paths = []
        for item in self.file_list.selectedItems():
            selected_paths.append(item.data(Qt.UserRole))

        if not selected_paths:
            self._log("[WARN] 请至少选择一个文件")
            return None

        kw_text = self.kw_input.text().strip()
        if not kw_text:
            self._log("[WARN] 请输入关键词")
            return None

        keywords = kw_text.split()
        field_choice = self.field_combo.currentData()
        match_mode = self.mode_combo.currentData() or MATCH_EXACT
        sort_order = self.sort_combo.currentData() or SORT_DESC
        return selected_paths, keywords, field_choice, match_mode, sort_order

    def _preview(self):
        """预览过滤结果（不写文件），弹出对话框确认后再输出"""
        params = self._get_params()
        if params is None:
            return
        selected_paths, keywords, field_choice, match_mode, sort_order = params

        # 预览在主线程执行（CPU 密集，数据量不大）
        self._set_buttons_enabled(False)
        try:
            items, has_nodate_file = self.txt_filter.preview(
                selected_paths, keywords, field_choice, match_mode, sort_order
            )
        finally:
            self._set_buttons_enabled(True)

        if not items:
            QMessageBox.information(self, "预览", "未匹配到任何行")
            return

        out_path = PreviewDialog.preview_and_confirm(
            items, has_nodate_file, self.txt_filter,
            selected_paths, keywords, sort_order, self
        )
        if out_path:
            self._log(f"[OK] 已输出: {out_path}")
        else:
            self._log("[INFO] 预览后取消，未输出文件")

    def _run_filter(self):
        """直接执行过滤（不预览）"""
        params = self._get_params()
        if params is None:
            return
        selected_paths, keywords, field_choice, match_mode, sort_order = params

        def _do():
            self.txt_filter.run(selected_paths, keywords, field_choice, match_mode, sort_order)

        self._run_worker(_do, "过滤中...")

    def _run_worker(self, func, text):
        if self.worker and self.worker.isRunning():
            return
        self.progress.start(text=text)
        self._set_buttons_enabled(False)
        self.btn_stop.setVisible(True)
        self.worker = ScraperWorker(func)
        mw = self.window()
        if hasattr(mw, "log_viewer"):
            self.worker.log_message.connect(mw.log_viewer.append_log)
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
        self.btn_run.setEnabled(enabled)
        self.btn_preview.setEnabled(enabled)
        self.kw_input.setEnabled(enabled)
        self.field_combo.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.sort_combo.setEnabled(enabled)
        self.file_list.setEnabled(enabled)

    def _log(self, msg):
        mw = self.window()
        if hasattr(mw, "log_viewer"):
            mw.log_viewer.append_log(msg)
