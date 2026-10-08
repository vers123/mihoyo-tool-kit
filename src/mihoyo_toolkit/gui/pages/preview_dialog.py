"""TXT 过滤预览对话框。

用 ``QTableView`` + :class:`MatchResultModel` 展示过滤排序后的完整结果，
确认后调用 :meth:`TxtFilter.export` 输出到文件。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...utils import MatchResult, TxtFilter
from ..models import MatchResultModel


class PreviewDialog(QDialog):
    """过滤结果预览对话框。

    Args:
        items: 已排序、待输出的匹配结果。
        txt_filter: 用于执行导出的过滤器实例。
        keywords: 关键词列表（仅用于信息栏展示）。
        ascending: 排序方向（仅用于信息栏展示）。
        parent: 父窗口。
    """

    def __init__(
        self,
        items: Sequence[MatchResult],
        txt_filter: TxtFilter,
        keywords: Sequence[str],
        ascending: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._items = list(items)
        self._txt_filter = txt_filter
        self._keywords = list(keywords)
        self._ascending = ascending
        self._output_path: Path | None = None

        self.setWindowTitle("过滤预览")
        self.resize(980, 620)
        self._model = MatchResultModel(self._items)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  属性
    # ------------------------------------------------------------------ #
    @property
    def output_path(self) -> Path | None:
        """确认输出后的文件路径；取消时为 ``None``。"""
        return self._output_path

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        info = QLabel(self._info_text())
        info.setWordWrap(True)
        layout.addWidget(info)

        table = QTableView()
        table.setModel(self._model)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.btn_modify = QPushButton("修改（返回编辑）")
        self.btn_modify.clicked.connect(self.reject)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("确认输出到文件")
        self.btn_confirm.setDefault(True)
        self.btn_confirm.clicked.connect(self._on_confirm)
        self.btn_confirm.setEnabled(bool(self._items))

        button_row.addWidget(self.btn_modify)
        button_row.addWidget(self.btn_cancel)
        button_row.addWidget(self.btn_confirm)
        layout.addLayout(button_row)

    def _info_text(self) -> str:
        sort_label = "时间升序" if self._ascending else "时间降序"
        text = (
            f"匹配 {len(self._items)} 行  |  关键词：{' / '.join(self._keywords)}"
            f"  |  排序：{sort_label}"
        )
        if self._items:
            first = self._items[0].timestamp or "（无日期）"
            last = self._items[-1].timestamp or "（无日期）"
            text += f"  |  首条 ~ 末条：{first} ~ {last}"
        return text

    # ------------------------------------------------------------------ #
    #  事件
    # ------------------------------------------------------------------ #
    def _on_confirm(self) -> None:
        if not self._items:
            return
        self._output_path = self._txt_filter.export(self._items, self._txt_filter.output_dir)
        self.accept()

    # ------------------------------------------------------------------ #
    #  便捷入口
    # ------------------------------------------------------------------ #
    @classmethod
    def confirm(
        cls,
        items: Sequence[MatchResult],
        txt_filter: TxtFilter,
        keywords: Sequence[str],
        ascending: bool = False,
        parent: QWidget | None = None,
    ) -> Path | None:
        """弹出对话框；用户确认输出时返回输出路径，否则返回 ``None``。"""
        dialog = cls(items, txt_filter, keywords, ascending, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.output_path
        return None


__all__ = ["PreviewDialog"]
