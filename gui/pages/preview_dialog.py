"""TXT 过滤预览对话框

弹出独立对话框，用 QTableWidget 展示过滤排序后的完整结果。
底部提供三个操作：确认输出到文件 / 修改（返回）/ 取消。
"""

from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt

from extractors.txt_filter import TxtFilter


class PreviewDialog(QDialog):
    """过滤预览对话框

    Args:
        items: filter_and_sort 返回的排序重编号后的 items
        has_nodate_file: 是否有无日期文件的提示
        txt_filter: TxtFilter 实例（用于确认输出时调用 write_to_file）
        file_paths: 原始文件路径列表（用于输出命名）
        keywords: 关键词列表（用于输出命名）
        parent: 父窗口
    """

    def __init__(
        self,
        items: List[Dict],
        has_nodate_file: bool,
        txt_filter: TxtFilter,
        file_paths: List[str],
        keywords: List[str],
        parent=None,
    ):
        super().__init__(parent)
        self._items = items
        self._has_nodate_file = has_nodate_file
        self._txt_filter = txt_filter
        self._file_paths = file_paths
        self._keywords = keywords
        self._output_path: Optional[str] = None

        self.setWindowTitle("过滤预览")
        self.resize(900, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # ---- 统计信息 ----
        n = len(self._items)
        kw_str = " / ".join(self._keywords)
        info_text = (
            f"匹配 {n} 行  |  关键词: {kw_str}  |  "
        )
        if self._items:
            latest = self._items[0].get("date", "(无日期)")
            oldest = self._items[-1].get("date", "(无日期)")
            info_text += f"时间范围: {oldest} ~ {latest}"
        if self._has_nodate_file:
            info_text += "  |  [提示] 部分文件无日期，已按原顺序排在末尾"

        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # ---- 表格 ----
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        headers = ["新序号", "原序号", "标题", "日期", "分类", "匹配关键词", "来源文件"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setRowCount(n)
        for row, item in enumerate(self._items):
            self._set_cell(row, 0, item.get("index", ""))
            self._set_cell(row, 1, item.get("old_index", ""))
            self._set_cell(row, 2, item.get("title", ""))
            self._set_cell(row, 3, item.get("date", "(无日期)"))
            self._set_cell(row, 4, item.get("category", ""))
            self._set_cell(row, 5, " / ".join(item.get("matched_keywords", [])))
            self._set_cell(row, 6, item.get("source_file", ""))

        # 列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 新序号
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 原序号
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # 标题
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 日期
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 分类
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 匹配关键词
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 来源文件

        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # ---- 底部按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_modify = QPushButton("修改（返回编辑）")
        self.btn_modify.clicked.connect(self._on_modify)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self._on_cancel)

        self.btn_confirm = QPushButton("确认输出到文件")
        self.btn_confirm.setDefault(True)
        self.btn_confirm.clicked.connect(self._on_confirm)

        btn_row.addWidget(self.btn_modify)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_confirm)
        layout.addLayout(btn_row)

        # 无匹配时禁用确认
        if n == 0:
            self.btn_confirm.setEnabled(False)

    def _set_cell(self, row: int, col: int, text: str):
        item = QTableWidgetItem(str(text))
        if col in (0, 1):  # 序号列居中对齐
            item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)

    # ---- 按钮事件 ----

    def _on_confirm(self):
        """确认输出到文件"""
        if not self._items:
            return
        out_path = self._txt_filter.write_to_file(
            self._items, self._file_paths, self._keywords
        )
        self._output_path = out_path
        self.accept()

    def _on_modify(self):
        """返回修改关键词/字段"""
        self.reject()

    def _on_cancel(self):
        """取消"""
        self.reject()

    @property
    def output_path(self) -> Optional[str]:
        """确认输出后的文件路径"""
        return self._output_path

    @staticmethod
    def preview_and_confirm(
        items: List[Dict],
        has_nodate_file: bool,
        txt_filter: TxtFilter,
        file_paths: List[str],
        keywords: List[str],
        parent=None,
    ) -> Optional[str]:
        """弹出预览对话框，用户确认后返回输出路径，否则 None"""
        dlg = PreviewDialog(
            items, has_nodate_file, txt_filter,
            file_paths, keywords, parent
        )
        dlg.exec()
        return dlg.output_path
