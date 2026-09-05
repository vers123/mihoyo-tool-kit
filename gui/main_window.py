"""GUI 主窗口 - 左侧导航栏 + 右侧内容区 + 底部全局日志面板"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from gui.theme import load_game_fonts, apply_light_theme, get_title_font, GAME_THEME_COLORS
from gui.widgets import LogViewer
from gui.pages import (
    GenshinNewsPage, GenshinENNewsPage, ZZZNewsPage, StarRailNewsPage,
    UserPostsPage, OtherPage, WeiboPage, SystemPage
)


class MainWindow(QMainWindow):
    """主窗口"""

    NAV_ITEMS = [
        ("原神新闻", "genshin"),
        ("原神新闻(EN)", "genshin_en"),
        ("绝区零新闻", "zzz"),
        ("星穹铁道新闻", "starrail"),
        ("米游社用户", None),
        ("其他抓取", None),
        ("微博", None),
        ("系统工具", None),
    ]

    def __init__(self):
        super().__init__()
        self.fonts = load_game_fonts()
        self._setup_ui()
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            apply_light_theme(app, self.fonts)

    def app(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()

    def _setup_ui(self):
        self.setWindowTitle("米游社工具箱 v5.0.0")
        self.resize(900, 650)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        for label, game_key in self.NAV_ITEMS:
            item = QListWidgetItem(label)
            if game_key and game_key in self.fonts:
                font = get_title_font(game_key, self.fonts, 14)
                item.setFont(font)
            self.nav_list.addItem(item)

        self.content_stack = QStackedWidget()
        self.pages = [
            GenshinNewsPage(),
            GenshinENNewsPage(),
            ZZZNewsPage(),
            StarRailNewsPage(),
            UserPostsPage(),
            OtherPage(),
            WeiboPage(),
            SystemPage(),
        ]
        for page in self.pages:
            self.content_stack.addWidget(page)

        top_layout.addWidget(self.nav_list)
        top_layout.addWidget(self.content_stack, 1)
        splitter.addWidget(top_widget)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(8, 4, 8, 4)
        log_layout.setSpacing(4)

        log_label = QLabel("日志输出")
        log_label.setStyleSheet("font-size: 12px; color: #6b7280; font-weight: bold; padding: 2px 0;")
        log_layout.addWidget(log_label)

        self.log_viewer = LogViewer()
        self.log_viewer.setMinimumHeight(150)
        self.log_viewer.setMaximumHeight(300)
        log_layout.addWidget(self.log_viewer)

        splitter.addWidget(log_widget)
        splitter.setSizes([450, 200])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        status = self.statusBar()
        status.showMessage("就绪")

    def _on_nav_changed(self, row):
        if 0 <= row < len(self.pages):
            self.content_stack.setCurrentIndex(row)
            label, game_key = self.NAV_ITEMS[row]
            color = GAME_THEME_COLORS.get(game_key, "#6b7280") if game_key else "#6b7280"
            self.statusBar().showMessage(f"当前: {label}")
