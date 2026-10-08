"""Qt 表格数据模型（MVC 的 Model 层）。

* :class:`GenericTableModel` —— 通用只读表格模型：由 ``loader`` 拉数据、
  ``getters`` 渲染单元格，供帖子 / 微博 / 匹配结果复用。
* :class:`NewsTableModel` —— 四站点新闻表格（序号 / 游戏 / 标题 / 日期 /
  分类 / 摘要 / 链接），数据来自 :meth:`Storage.query_news`。
* :class:`MatchResultModel` —— TXT 过滤预览结果。

模型只读，不直接执行抓取逻辑；数据刷新由 Controller / 页面在任务结束后调用。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, ClassVar

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
)

from ..core import Storage
from ..core.models import NewsItem

#: Qt 索引参数（重载需与父类签名一致）
Index = QModelIndex | QPersistentModelIndex

#: 单元格渲染函数：实体 -> 字符串
CellGetter = Callable[[Any], object]
#: 数据加载函数：返回实体序列
RowLoader = Callable[[], Sequence[Any]]


class GenericTableModel(QAbstractTableModel):
    """通用只读表格模型。

    Args:
        headers: 列标题；``numbered=True`` 时首列标题为序号列。
        loader: 无参可调用对象，返回行数据（可在其中访问 Storage）。
        getters: 与「数据列」一一对应的单元格渲染函数。
        numbered: 是否在最左侧插入自增序号列。
    """

    def __init__(
        self,
        headers: Sequence[str],
        loader: RowLoader,
        getters: Sequence[CellGetter],
        *,
        numbered: bool = False,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._headers = list(headers)
        self._loader = loader
        self._getters = list(getters)
        self._numbered = numbered
        self._rows: list[Any] = []
        #: 最近一次加载失败的原因（成功时为 None）
        self.last_error: str | None = None

    # ------------------------------------------------------------------ #
    #  QAbstractTableModel 接口
    # ------------------------------------------------------------------ #
    def rowCount(self, parent: Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
            return None
        return section + 1

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return None
        column = index.column()
        if self._numbered and column == 0:
            return str(index.row() + 1)
        return self._cell_text(self._rows[index.row()], column)

    # ------------------------------------------------------------------ #
    #  数据装载
    # ------------------------------------------------------------------ #
    def reload(self) -> int:
        """重新执行 ``loader`` 并刷新全部行，返回行数。"""
        self.last_error = None
        try:
            rows = list(self._loader())
        except Exception as exc:
            rows = []
            self.last_error = str(exc)
        self.set_rows(rows)
        return len(rows)

    def set_rows(self, rows: Sequence[Any]) -> None:
        """直接替换全部行（供已持有数据的场景，如预览对话框）。"""
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    @property
    def rows(self) -> list[Any]:
        """当前行数据的副本。"""
        return list(self._rows)

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #
    def _cell_text(self, row: Any, column: int) -> str:
        getter_index = column - 1 if self._numbered else column
        if getter_index < 0 or getter_index >= len(self._getters):
            return ""
        try:
            value = self._getters[getter_index](row)
        except Exception:
            return ""
        return "" if value is None else str(value)


class NewsTableModel(GenericTableModel):
    """新闻表格模型：序号 / 游戏 / 标题 / 日期 / 分类 / 摘要 / 链接。"""

    HEADERS: ClassVar[list[str]] = ["序号", "游戏", "标题", "日期", "分类", "摘要", "链接"]

    def __init__(self, game: str, parent: Any = None) -> None:
        super().__init__(
            self.HEADERS,
            lambda: self._load(game),
            [
                lambda item: item.game,
                lambda item: item.sTitle,
                lambda item: item.dtStartTime,
                lambda item: item.sCategoryName,
                lambda item: item.sIntro,
                lambda item: item.url,
            ],
            numbered=True,
            parent=parent,
        )
        self.game = game

    @staticmethod
    def _load(game: str) -> list[NewsItem]:
        with Storage() as store:
            return store.query_news(game)


class MatchResultModel(GenericTableModel):
    """TXT 过滤预览表格模型。"""

    HEADERS: ClassVar[list[str]] = [
        "新序号",
        "行号",
        "时间",
        "命中关键词",
        "来源文件",
        "内容",
    ]

    def __init__(self, items: Sequence[Any], parent: Any = None) -> None:
        super().__init__(
            self.HEADERS,
            lambda: items,
            [
                lambda item: item.line_no,
                lambda item: item.timestamp or "（无日期）",
                lambda item: " / ".join(item.matched_keywords),
                lambda item: item.source_file,
                lambda item: item.text,
            ],
            numbered=True,
            parent=parent,
        )
        self.set_rows(items)


__all__ = [
    "CellGetter",
    "GenericTableModel",
    "MatchResultModel",
    "NewsTableModel",
    "RowLoader",
]
