"""首页：官网风卡片入口。

以卡片网格展示各功能分组（标题 + 一行说明 + 动作数），点击卡片跳到对应页面。
卡片信息全部来自导航项（即 CLI 命令注册表派生结果），不额外维护一份清单。
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ... import __version__
from .. import theme

#: 卡片网格最大列数（窗口变窄时自动降为 1 列）
_MAX_COLUMNS = 3

#: 卡片最小宽度（像素），用于计算列数
_CARD_MIN_WIDTH = 300


class HomeCard(QFrame):
    """一张可点击的分组卡片。"""

    clicked = Signal()

    def __init__(self, title: str, description: str, actions: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("homeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(112)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            theme.CARD_PADDING, theme.CARD_PADDING - 4, theme.CARD_PADDING, theme.CARD_PADDING - 4
        )
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        header.addWidget(title_label)
        header.addStretch()
        count_label = QLabel(f"{actions} 个动作")
        count_label.setObjectName("cardCount")
        header.addWidget(count_label)
        layout.addLayout(header)

        desc_label = QLabel(description or "点击进入")
        desc_label.setObjectName("cardDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        layout.addStretch()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """左键释放时触发跳转。"""
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class HomePage(QWidget):
    """首页卡片网格。

    Signals:
        navigate: 请求跳转到指定导航行（0 为首页自身）。
    """

    navigate = Signal(int)

    def __init__(self, cards: Sequence[tuple[str, str, int]] = (), parent: QWidget | None = None):
        super().__init__(parent)
        self._cards = list(cards)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(6)

        title = QLabel("米游社工具箱")
        title.setObjectName("pageTitle")
        title_font = title.font()
        title_font.setPointSizeF(title_font.pointSizeF() + theme.TITLE_OFFSET + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        outer.addWidget(title)

        subtitle = QLabel(
            f"v{__version__} · 米游社 / 微博 / 米哈游四站点新闻抓取与提取 · 选择下方功能卡片开始"
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)
        outer.addSpacing(8)

        divider = QFrame()
        divider.setObjectName("pageHeaderDivider")
        divider.setFixedHeight(1)
        outer.addWidget(divider)
        outer.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll = scroll

        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(theme.CARD_SPACING)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        self._build_cards()

    def _columns(self) -> int:
        """按当前可用宽度计算列数（1..``_MAX_COLUMNS``）。"""
        viewport = self._scroll.viewport()
        width = viewport.width() if viewport is not None else self.width()
        if width <= 0:
            width = self.width()
        return max(1, min(_MAX_COLUMNS, max(1, width // _CARD_MIN_WIDTH)))

    def _build_cards(self) -> None:
        """按当前卡片数量重新排布网格。

        导航行 0 是首页自身，因此第 ``i`` 张卡片对应导航行 ``i + 1``。
        """
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        columns = self._columns()
        for index, (title, description, actions) in enumerate(self._cards):
            card = HomeCard(title, description, actions, self)
            card.clicked.connect(lambda row=index + 1: self.navigate.emit(row))
            self._grid.addWidget(card, index // columns, index % columns)

        # 末尾补一个伸缩行，避免卡片被拉伸到整列
        self._grid.setRowStretch((len(self._cards) + columns - 1) // columns, 1)

    def set_cards(self, cards: Sequence[tuple[str, str, int]]) -> None:
        """替换卡片数据并重建网格。"""
        self._cards = list(cards)
        self._build_cards()

    # ------------------------------------------------------------------ #
    #  尺寸变化
    # ------------------------------------------------------------------ #
    def showEvent(self, event) -> None:
        """首次显示后按最终宽度重排（布局完成前视口宽度还不可靠）。"""
        super().showEvent(event)
        QTimer.singleShot(0, self._build_cards)

    def resizeEvent(self, event) -> None:
        """宽度变化导致列数变化时重排。"""
        super().resizeEvent(event)
        current_columns = self._grid.columnCount() or 1
        if self._columns() != current_columns:
            self._build_cards()


__all__ = ["HomeCard", "HomePage"]
