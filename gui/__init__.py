"""GUI 模块入口"""

import os
import sys

from gui.main_window import MainWindow
from gui.fonts import load_game_fonts
from gui.paths import get_app_icon_path


def launch_gui():
    """启动 GUI 应用

    使用 PySide6 平台默认原生风格，不应用自定义 QSS。
    字体默认使用系统字体；游戏字体已加载到 QFontDatabase 供设置页按需调用。
    """
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QTextBrowser,
        QPushButton, QHBoxLayout,
    )
    from PySide6.QtGui import QIcon

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("米游社工具箱")
    app.setOrganizationName("miHoYo ToolKit")

    # 设置应用图标（任务栏、窗口左上角）
    icon_path = get_app_icon_path()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 加载游戏字体到数据库（不自动应用，预留设置页接口）
    fonts = load_game_fonts()

    # 启动欢迎弹窗：提示用户更新 HAR 文件（文本可选中复制，链接可点击打开浏览器）
    from utils.har_loader import get_har_welcome_html

    welcome_dlg = QDialog()
    welcome_dlg.setWindowTitle("欢迎使用 米游社工具箱")
    welcome_dlg.resize(620, 560)

    dlg_layout = QVBoxLayout(welcome_dlg)
    dlg_layout.setContentsMargins(16, 14, 16, 14)
    dlg_layout.setSpacing(10)

    # QTextBrowser：只读、支持文本选中复制、HTML 渲染、链接点击
    text_browser = QTextBrowser()
    text_browser.setReadOnly(True)
    text_browser.setOpenExternalLinks(True)  # 点击链接用系统默认浏览器打开
    text_browser.setHtml(get_har_welcome_html())
    dlg_layout.addWidget(text_browser)

    # 底部确定按钮
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    ok_btn = QPushButton("确定")
    ok_btn.setDefault(True)
    ok_btn.clicked.connect(welcome_dlg.accept)
    btn_row.addWidget(ok_btn)
    dlg_layout.addLayout(btn_row)

    welcome_dlg.exec()

    window = MainWindow()
    window.fonts = fonts
    window.show()

    sys.exit(app.exec())


__all__ = ["launch_gui", "MainWindow", "get_app_icon_path"]
