"""GUI 主窗口：品牌栏 + 左侧导航 + 右侧内容区 + 底部全局日志面板。

布局参考 mihoyo.com：顶部品牌栏（应用名 / 版本 / 三态主题切换），下方左侧导航
（选中为品牌色胶囊）+ 右侧内容区，底部为日志面板。首页为卡片网格入口，导航项
由 CLI 命令注册表派生（见 :mod:`mihoyo_toolkit.gui.nav`）。
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
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
        theme_mode: 覆盖本次会话的主题模式（``auto``/``light``/``dark``）；
            为 ``None`` 时读取 ``data/ui_state.json`` 中持久化的偏好。
            截图脚本用它保证输出可复现。
    """

    def __init__(
        self,
        fonts: dict[str, str] | None = None,
        parent: QWidget | None = None,
        *,
        theme_mode: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.fonts: dict[str, str] = dict(fonts or {})
        self._initial_theme_mode = theme_mode
        self._pages: list[QWidget] = []
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        self.setWindowTitle(f"米游社工具箱 v{__version__}")
        self.resize(1040, 720)
        # 样式表由 QApplication 统一持有（见 gui._ensure_application）；
        # 窗口级再设一份会让每次主题切换多付一次全量重绘。
        self._ensure_app_stylesheet()

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

    @staticmethod
    def _ensure_app_stylesheet() -> None:
        """独立使用 MainWindow（未经 launch_gui）时补一次应用级样式表。"""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if not isinstance(app, QApplication) or app.styleSheet():
            return
        theme.apply_to_application(app, theme.resolve_mode())

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

        current_mode = (
            theme.set_mode(self._initial_theme_mode)
            if self._initial_theme_mode is not None
            else ui_state.load_theme_mode()
        )
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
        """切换主题：立即换色，日志重着色排到下一轮事件循环。

        主题切换的主要开销是「应用级样式表重绘」（~190ms）与「日志面板按语义
        重新着色」（几千行时 ~170ms）。前者必须同步（否则界面先闪旧配色），
        后者对观感无影响，故延后执行，点击后立刻就能看到新主题。
        """
        from PySide6.QtWidgets import QApplication

        if mode == theme.current_mode():
            return  # 已经是该主题：避免不必要的全量重绘

        theme.set_mode(mode)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            # 只更新调色板 + 样式表（不再重复 setStyle，避免数百 ms 的全量重绘）
            theme.apply_to_application(app, theme.resolve_mode())

        ui_state.save_theme_mode(mode)
        self.statusBar().showMessage(f"主题：{theme.MODE_LABELS[theme.current_mode()]}")
        QTimer.singleShot(0, self.apply_theme)

    def apply_theme(self) -> None:
        """按当前主题模式刷新界面。

        应用级样式表已由 :func:`theme.apply_to_application` 更新，这里只重绘
        日志面板（它按语义着色，无法通过 QSS 表达）。
        """
        self.log_viewer.reapply_theme()


__all__ = ["HOME_TITLE", "MainWindow"]
