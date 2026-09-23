"""GUI 主窗口 - 左侧导航栏 + 右侧内容区 + 底部全局日志面板

使用 PySide6 平台默认原生风格，不应用自定义 QSS。
字体默认使用系统字体；游戏字体由 gui.fonts.load_game_fonts 加载到数据库，
预留供未来设置页按需调用（不自动应用到导航栏）。
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from gui.paths import get_app_icon_path

from gui.widgets import LogViewer
from gui.pages import (
    GenshinNewsPage, GenshinENNewsPage, ZZZNewsPage, StarRailNewsPage,
    UserPostsPage, OtherPage, WeiboPage, SystemPage, FilterPage
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
        ("TXT 过滤", None),
        ("系统工具", None),
    ]

    def __init__(self):
        super().__init__()
        # 字体字典由 launch_gui 注入；直接实例化时为空，使用系统默认字体
        self.fonts = {}
        self._setup_ui()

    def app(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()

    def _setup_ui(self):
        self.setWindowTitle("米游社工具箱 v1.3.0")
        self.resize(900, 650)

        # 设置窗口图标
        import os
        icon_path = get_app_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

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

        for label, _game_key in self.NAV_ITEMS:
            item = QListWidgetItem(label)
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
            FilterPage(),
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
            label, _game_key = self.NAV_ITEMS[row]
            self.statusBar().showMessage(f"当前: {label}")
