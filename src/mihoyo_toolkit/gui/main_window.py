"""GUI 主窗口：品牌栏 + 左侧导航 + 右侧内容区 + 底部全局日志面板。

布局参考 mihoyo.com：顶部品牌栏（应用名 / 版本 / 三态主题切换），下方左侧导航
（选中为品牌色胶囊）+ 右侧内容区，底部为日志面板。首页为卡片网格入口，导航项
由 CLI 命令注册表派生（见 :mod:`mihoyo_toolkit.gui.nav`）。
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from . import theme, ui_state
from .fonts import get_title_font
from .nav import NavEntry, build_nav
from .pages.home import HomePage
from .paths import load_app_icon
from .widgets import LogViewer

#: 品牌栏高度
_BRAND_BAR_HEIGHT = 56

#: 首页导航项的标题
HOME_TITLE = "首页"


class MainWindow(QMainWindow):
    """工具箱主窗口。

    Args:
        fonts: ``load_game_fonts()`` 的返回值，用于导航项的游戏字体；
            为空字典时全部使用系统默认字体。
    """

    def __init__(self, fonts: dict[str, str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.fonts: dict[str, str] = dict(fonts or {})
        self._pages: list[QWidget] = []
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

        main_layout.addWidget(self._build_brand_bar())

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self.splitter, 1)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFixedWidth(theme.NAV_WIDTH)

        # 导航项来自 CLI 命令注册表；首页固定在最前
        self.nav_entries: list[NavEntry] = self._with_home(build_nav())

        self.content_stack = QStackedWidget()
        self._pages = self._create_pages()
        for page in self._pages:
            self.content_stack.addWidget(page)
            log_signal = getattr(page, "log_message", None)
            if log_signal is not None:
                log_signal.connect(self._append_log)

        self._fill_nav()
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        top_layout.addWidget(self.nav_list)
        top_layout.addWidget(self.content_stack, 1)
        self.splitter.addWidget(top)

        self.splitter.addWidget(self._build_log_panel())
        for page in self._pages:
            progress_signal = getattr(page, "progress_message", None)
            if progress_signal is not None:
                progress_signal.connect(self.log_viewer.update_progress)
        self.splitter.setSizes([520, 200])
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        self.nav_list.setCurrentRow(0)
        self.statusBar().showMessage("就绪")

    def _with_home(self, entries: list[NavEntry]) -> list[NavEntry]:
        """在导航列表最前插入首页项（不参与命令覆盖校验）。"""
        home = NavEntry(key="home", title=HOME_TITLE, commands=(), factory=HomePage)
        return [home, *entries]

    def _fill_nav(self) -> None:
        """渲染导航项（首页使用普通字体，其余项可用游戏字体）。"""
        for entry in self.nav_entries:
            item = QListWidgetItem(entry.title)
            if entry.key in self.fonts:
                item.setFont(get_title_font(entry.key, self.fonts, 13))
            # 显式统一行高：游戏字体度量差异 + QSS padding 会让 Qt 忽略字体推导高度，
            # 导致行高不一致与文字重叠
            item.setSizeHint(QSize(0, theme.NAV_ITEM_HEIGHT))
            self.nav_list.addItem(item)

    def _build_brand_bar(self) -> QWidget:
        """顶部品牌栏：应用名 + 版本 + 三态主题切换。"""
        bar = QFrame()
        bar.setObjectName("brandBar")
        bar.setFixedHeight(_BRAND_BAR_HEIGHT)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(10)

        icon = load_app_icon()
        if icon is not None:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(22, 22))
            layout.addWidget(icon_label)

        title = QLabel("米游社工具箱")
        title.setObjectName("brandTitle")
        layout.addWidget(title)

        version = QLabel(f"v{__version__}")
        version.setObjectName("brandVersion")
        layout.addWidget(version)
        layout.addStretch()

        self._theme_group = QButtonGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_buttons: dict[str, QToolButton] = {}

        current_mode = ui_state.load_theme_mode()
        theme.set_mode(current_mode)
        for mode, label in theme.MODE_LABELS.items():
            button = QToolButton()
            button.setObjectName("themeSegment")
            button.setText(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, m=mode: self._on_theme_mode(m))
            self._theme_group.addButton(button)
            layout.addWidget(button)
            self._theme_buttons[mode] = button
            if mode == current_mode:
                button.setChecked(True)

        return bar

    def _build_log_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("logPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 8, 16, 10)
        layout.setSpacing(6)

        title = QLabel("日志输出")
        title.setObjectName("logTitle")
        layout.addWidget(title)

        self.log_viewer = LogViewer()
        self.log_viewer.setMinimumHeight(130)
        layout.addWidget(self.log_viewer)
        return panel

    def _create_pages(self) -> list[QWidget]:
        """按导航项创建页面；首页额外注入卡片数据（标题 / 说明 / 动作数）。"""
        pages: list[QWidget] = [entry.factory() for entry in self.nav_entries]
        home = next((page for page in pages if isinstance(page, HomePage)), None)
        if isinstance(home, HomePage):
            cards = [
                (entry.title, self._entry_description(entry), len(entry.commands))
                for entry in self.nav_entries
                if entry.key != "home"
            ]
            home.set_cards(cards)
            home.navigate.connect(self.select_page)
        return pages

    @staticmethod
    def _entry_description(entry: NavEntry) -> str:
        """取导航项的一行说明（分组页取首条命令描述，单命令页取自身描述）。"""
        from ..cli.registry import registry

        for key in entry.commands:
            command = registry.get(key)
            if command is not None and command.description:
                return command.description
        return ""

    # ------------------------------------------------------------------ #
    #  槽函数
    # ------------------------------------------------------------------ #
    def select_page(self, row: int) -> bool:
        """切换到指定导航行；越界返回 ``False``。"""
        if not 0 <= row < self.nav_list.count():
            return False
        self.nav_list.setCurrentRow(row)
        return True

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < len(self._pages):
            self.content_stack.setCurrentIndex(row)
            self.statusBar().showMessage(f"当前：{self.nav_entries[row].title}")

    def _append_log(self, message: str) -> None:
        self.log_viewer.append_log(message)

    def _on_theme_mode(self, mode: str) -> None:
        """切换主题：立即重绘并持久化偏好。"""
        from PySide6.QtWidgets import QApplication

        theme.set_mode(mode)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            theme.apply_to_application(app, theme.resolve_mode())
        self.apply_theme()
        ui_state.save_theme_mode(mode)
        self.statusBar().showMessage(f"主题：{theme.MODE_LABELS[theme.current_mode()]}")

    def apply_theme(self) -> None:
        """按当前主题模式刷新窗口样式与日志配色。"""
        self.setStyleSheet(theme.app_stylesheet())
        self.log_viewer.reapply_theme()


__all__ = ["HOME_TITLE", "MainWindow"]
