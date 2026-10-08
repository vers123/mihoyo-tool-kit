"""GUI 主窗口：左侧导航 + 右侧内容区 + 底部全局日志面板。"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from . import theme
from .fonts import get_title_font
from .nav import NavEntry, build_nav
from .pages.base import BasePage
from .paths import load_app_icon
from .widgets import LogViewer


class MainWindow(QMainWindow):
    """工具箱主窗口。

    导航由 CLI 命令注册表派生（见 :mod:`mihoyo_toolkit.gui.nav`），因此界面与
    交互菜单始终共用同一份命令清单。

    Args:
        fonts: ``load_game_fonts()`` 的返回值，用于导航项的游戏字体；
            为空字典时全部使用系统默认字体。
    """

    def __init__(self, fonts: dict[str, str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.fonts: dict[str, str] = dict(fonts or {})
        self._pages: list[BasePage] = []
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        self.setWindowTitle(f"米游社工具箱 v{__version__}")
        self.resize(1040, 720)
        self.setStyleSheet(theme.app_stylesheet())

        icon = load_app_icon()
        if icon is not None:
            self.setWindowIcon(icon)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self.splitter)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFixedWidth(theme.NAV_WIDTH)

        # 导航项来自 CLI 命令注册表：菜单与界面共用同一份命令清单
        self.nav_entries: list[NavEntry] = build_nav()

        self.content_stack = QStackedWidget()
        self._pages = self._create_pages()
        for page in self._pages:
            self.content_stack.addWidget(page)
            page.log_message.connect(self._append_log)

        for entry in self.nav_entries:
            item = QListWidgetItem(entry.title)
            if entry.key in self.fonts:
                item.setFont(get_title_font(entry.key, self.fonts, 13))
            # 显式统一行高：游戏字体度量差异 + QSS padding 会让 Qt 忽略字体推导高度，
            # 导致行高不一致与文字重叠
            item.setSizeHint(QSize(0, theme.NAV_ITEM_HEIGHT))
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        top_layout.addWidget(self.nav_list)
        top_layout.addWidget(self.content_stack, 1)
        self.splitter.addWidget(top)

        self.splitter.addWidget(self._build_log_panel())
        self.splitter.setSizes([500, 220])
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        self.nav_list.setCurrentRow(0)
        self.statusBar().showMessage("就绪")

    def _build_log_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        layout.addWidget(QLabel("日志输出"))
        self.log_viewer = LogViewer()
        self.log_viewer.setMinimumHeight(140)
        layout.addWidget(self.log_viewer)
        return panel

    def _create_pages(self) -> list[BasePage]:
        """按导航项（即注册表派生结果）创建页面。"""
        return [entry.factory() for entry in self.nav_entries]

    # ------------------------------------------------------------------ #
    #  槽函数
    # ------------------------------------------------------------------ #
    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < len(self._pages):
            self.content_stack.setCurrentIndex(row)
            self.statusBar().showMessage(f"当前：{self.nav_entries[row].title}")

    def _append_log(self, message: str) -> None:
        self.log_viewer.append_log(message)

    def apply_theme(self) -> None:
        """按当前（系统）主题刷新窗口样式与日志配色。

        由 :func:`~mihoyo_toolkit.gui._watch_system_theme` 在系统
        深浅色切换时调用。
        """
        self.setStyleSheet(theme.app_stylesheet())
        self.log_viewer.reapply_theme()


__all__ = ["MainWindow"]
