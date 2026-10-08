"""TXT 文件过滤页面。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ...core import get_path_manager
from ...utils import MatchResult, TxtFilter
from .base import BasePage
from .preview_dialog import PreviewDialog

#: 匹配模式下拉项：(显示文本, 是否模糊匹配)
_MATCH_MODES: tuple[tuple[str, bool], ...] = (
    ("精确匹配（完整子串）", False),
    ("模糊匹配（2-gram）", True),
)

#: 排序方向下拉项：(显示文本, 是否升序)
_SORT_ORDERS: tuple[tuple[str, bool], ...] = (
    ("时间降序（最新在前）", False),
    ("时间升序（最早在前）", True),
)


class FilterPage(BasePage):
    """按关键词过滤 TXT 文件、排序重编号并导出。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.txt_filter = TxtFilter()
        self._file_entries: list[tuple[str, Path, int]] = []
        self._pending_action = ""
        self._keywords: list[str] = []
        self._ascending = False
        self._setup_ui()
        self.refresh_files()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(
            self.make_header("TXT 过滤", "按关键词匹配提取行，按时间升序 / 降序重新编号")
        )

        layout.addWidget(self._build_file_group())
        layout.addWidget(self._build_option_group())

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addStretch()
        self.btn_preview = self.make_button("预览", self._preview)
        self.btn_run = self.make_button("执行过滤", self._run_filter)
        button_row.addWidget(self.btn_preview)
        button_row.addWidget(self.btn_run)
        button_row.addWidget(self.btn_stop)
        layout.addLayout(button_row)

        layout.addWidget(self.progress)
        layout.addStretch()

        self.register_buttons(self.btn_preview, self.btn_run)

    def _build_file_group(self) -> QGroupBox:
        group = QGroupBox("可用文件（可多选）")
        group_layout = QVBoxLayout(group)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.file_list.setMaximumHeight(180)
        group_layout.addWidget(self.file_list)

        refresh_button = self.make_button("刷新列表", self.refresh_files)
        group_layout.addWidget(refresh_button)
        return group

    def _build_option_group(self) -> QGroupBox:
        group = QGroupBox("关键词与匹配设置")
        group_layout = QVBoxLayout(group)

        keyword_row = QHBoxLayout()
        keyword_row.addWidget(QLabel("关键词："))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("多个关键词用空格分隔（OR 逻辑）")
        keyword_row.addWidget(self.kw_input)
        group_layout.addLayout(keyword_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("匹配模式："))
        self.mode_combo = QComboBox()
        for label, fuzzy in _MATCH_MODES:
            self.mode_combo.addItem(label, fuzzy)
        mode_row.addWidget(self.mode_combo)

        mode_row.addWidget(QLabel("排序方向："))
        self.sort_combo = QComboBox()
        for label, ascending in _SORT_ORDERS:
            self.sort_combo.addItem(label, ascending)
        mode_row.addWidget(self.sort_combo)
        mode_row.addStretch()
        group_layout.addLayout(mode_row)
        return group

    # ------------------------------------------------------------------ #
    #  文件列表
    # ------------------------------------------------------------------ #
    def refresh_files(self) -> None:
        """重新扫描可过滤的 TXT 文件。"""
        self.file_list.clear()
        try:
            self._file_entries = self.txt_filter.list_txt_files()
        except Exception as exc:
            self._file_entries = []
            self.log_message.emit(f"[ERROR] 扫描 TXT 文件失败：{exc}")
            return

        for relative, path, count in self._file_entries:
            item = QListWidgetItem(f"{relative}（{count} 行）")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.file_list.addItem(item)

        if not self._file_entries:
            self.log_message.emit("[WARN] 未找到可过滤的 TXT 文件")

    # ------------------------------------------------------------------ #
    #  动作
    # ------------------------------------------------------------------ #
    def _preview(self) -> None:
        params = self._collect_params()
        if params is None:
            return
        self._pending_action = "preview"
        self.run_task(self._make_task(*params), "过滤预览中…")

    def _run_filter(self) -> None:
        params = self._collect_params()
        if params is None:
            return
        self._pending_action = "export"
        self.run_task(self._make_task(*params), "执行过滤中…")

    def _collect_params(self) -> tuple[list[Path], list[str], bool, bool] | None:
        paths = [item.data(Qt.ItemDataRole.UserRole) for item in self.file_list.selectedItems()]
        if not paths:
            self.log_message.emit("[WARN] 请至少选择一个文件")
            return None

        keywords = self.kw_input.text().split()
        if not keywords:
            self.log_message.emit("[WARN] 请输入关键词")
            return None

        fuzzy = bool(self.mode_combo.currentData())
        ascending = bool(self.sort_combo.currentData())
        self._keywords = keywords
        self._ascending = ascending
        return paths, keywords, fuzzy, ascending

    # ------------------------------------------------------------------ #
    #  后台任务
    # ------------------------------------------------------------------ #
    def _make_task(
        self, paths: list[Path], keywords: list[str], fuzzy: bool, ascending: bool
    ) -> Callable[[], object]:
        """构造在后台线程执行的任务闭包。"""

        def task() -> object:
            results = self._filter_files(paths, keywords, fuzzy, ascending)
            if self._pending_action != "export":
                return results
            if not results:
                return None
            return self.txt_filter.export(results, self.txt_filter.output_dir)

        return task

    def _filter_files(
        self, paths: list[Path], keywords: list[str], fuzzy: bool, ascending: bool
    ) -> list[MatchResult]:
        """逐文件过滤并合并排序（在后台线程执行）。"""
        total = len(paths)
        results: list[MatchResult] = []
        for index, path in enumerate(paths, 1):
            self.controller.report_progress(int(index * 100 / total))
            results.extend(
                self.txt_filter.filter_file(path, keywords, fuzzy=fuzzy, ascending=ascending)
            )
        dated = sorted(
            (item for item in results if item.timestamp),
            key=lambda item: item.timestamp,
            reverse=not ascending,
        )
        undated = [item for item in results if not item.timestamp]
        return dated + undated

    # ------------------------------------------------------------------ #
    #  任务回调
    # ------------------------------------------------------------------ #
    def _on_task_finished(self, result: object) -> None:
        action, self._pending_action = self._pending_action, ""
        self._restore_controls()

        if action == "preview":
            self.progress.finish("预览完成")
            self._show_preview(result)
            return

        if isinstance(result, Path):
            relative = get_path_manager().relative(result)
            self.progress.finish(f"已导出：{relative}")
            self.log_message.emit(f"[OK] 输出路径：{relative}")
        else:
            self.progress.reset("没有匹配到任何行")

    def _show_preview(self, result: object) -> None:
        items = list(result) if isinstance(result, list) else []
        if not items:
            QMessageBox.information(self, "预览", "未匹配到任何行")
            return

        output_path = PreviewDialog.confirm(
            items, self.txt_filter, self._keywords, self._ascending, self
        )
        if output_path is None:
            self.log_message.emit("[INFO] 已取消输出")
            return
        self.log_message.emit(f"[OK] 输出路径：{get_path_manager().relative(output_path)}")

    def _on_task_failed(self, message: str) -> None:
        self._pending_action = ""
        super()._on_task_failed(message)

    def _on_task_cancelled(self) -> None:
        self._pending_action = ""
        super()._on_task_cancelled()


__all__ = ["FilterPage"]
