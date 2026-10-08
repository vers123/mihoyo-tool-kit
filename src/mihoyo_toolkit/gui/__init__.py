"""GUI 包入口：``launch_gui()`` 启动 PySide6 界面。

除 ``launch_gui`` 外，本模块还导出 :class:`MainWindow` 便于外部（如
``mihoyo_toolkit.__main__``）自行构建窗口。
"""

from __future__ import annotations

import sys

from .fonts import load_game_fonts
from .main_window import MainWindow
from .nav import NavEntry, build_nav
from .paths import load_app_icon

__all__ = ["MainWindow", "NavEntry", "build_nav", "launch_gui"]


def _ensure_application():
    """创建或复用 ``QApplication`` 单例，并应用跟随系统的主题与图标。"""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from . import theme

    app = QApplication.instance()
    if app is not None:
        return app

    # 高 DPI 必须在 QApplication 创建前设置
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("米游社工具箱")
    app.setOrganizationName("miHoYo ToolKit")

    # 自动跟随系统深浅色：Fusion 样式 + 与系统匹配的调色板/样式表
    theme.apply_to_application(app)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)
    return app


def _watch_system_theme(app, window: MainWindow) -> None:
    """监听系统深浅色变化并实时切换界面主题。"""
    from . import theme

    hints = app.styleHints()
    signal = getattr(hints, "colorSchemeChanged", None)
    if signal is None:  # pragma: no cover - Qt < 6.5
        return

    def _on_scheme_changed(*_args: object) -> None:
        theme.apply_to_application(app)
        window.apply_theme()

    signal.connect(_on_scheme_changed)


def _show_welcome_dialog() -> None:
    """显示 HAR 更新提示欢迎弹窗（文本可复制、链接可点击）。"""
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QPushButton,
        QTextBrowser,
        QVBoxLayout,
    )

    from ..utils import get_har_welcome_html

    try:
        html = get_har_welcome_html()
    except Exception as exc:
        html = f"<p>无法加载欢迎信息：{exc}</p>"

    dialog = QDialog()
    dialog.setWindowTitle("欢迎使用 米游社工具箱")
    dialog.resize(680, 560)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)

    browser = QTextBrowser()
    browser.setReadOnly(True)
    browser.setOpenExternalLinks(True)
    browser.setHtml(html)
    layout.addWidget(browser)

    button_row = QHBoxLayout()
    button_row.addStretch()
    confirm = QPushButton("确定")
    confirm.setDefault(True)
    confirm.clicked.connect(dialog.accept)
    button_row.addWidget(confirm)
    layout.addLayout(button_row)

    dialog.exec()


def launch_gui() -> None:
    """创建 ``QApplication``、显示欢迎弹窗与主窗口，然后进入事件循环。

    主题自动跟随系统深浅色；资源（图标 / 游戏字体）缺失时会自动降级，
    不会中断启动。
    """
    app = _ensure_application()
    fonts = load_game_fonts()
    _show_welcome_dialog()

    window = MainWindow(fonts=fonts)
    _watch_system_theme(app, window)
    window.show()
    app.exec()
