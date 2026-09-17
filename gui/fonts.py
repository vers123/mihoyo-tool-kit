"""GUI 字体加载工具

预留字体设置接口：未来可在 SystemPage / 设置页中让用户选择游戏字体或系统字体。
当前默认使用系统原生字体，不自动应用游戏字体。
"""

import os
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
from core.config_manager import config_manager

FONT_DIR = os.path.join(config_manager.get_project_root(), "resources", "font")

GAME_TITLE_FONTS = {
    "genshin":  "Genshin Impact/Teyvat-Black/ttf/TeyvatBlack-Regular.ttf",
    "starrail": "Star Rail/Star-Rail-Neue/ttf/StarRailNeue-Sans-Regular.ttf",
    "zzz":      "ZenlessZoneZero/ZZZ-System/ttf/ZZZSystem-Regular.ttf",
}

GAME_BODY_FONTS = {
    "zzz_body": "ZenlessZoneZero/ZZZ-A/ttf/ZZZA-Regular.ttf",
}


def load_game_fonts() -> dict:
    """加载所有游戏字体到 QFontDatabase，返回 {key: family_name}

    仅加载到数据库，不自动应用。返回的 family 名可供后续调用 setFont 使用。
    """
    loaded = {}
    all_fonts = {**GAME_TITLE_FONTS, **GAME_BODY_FONTS}
    for key, rel_path in all_fonts.items():
        font_path = os.path.join(FONT_DIR, rel_path)
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    loaded[key] = families[0]
    return loaded


def get_title_font(game_key: str, fonts: dict, size: int = 18) -> QFont:
    """获取指定游戏的标题字体

    Args:
        game_key: "genshin" / "starrail" / "zzz"
        fonts: load_game_fonts() 返回的字典
        size: 字号
    """
    family = fonts.get(game_key, "Microsoft YaHei")
    return QFont(family, size, QFont.Bold)


def apply_app_font(app: QApplication, family: str = "", size: int = 14):
    """应用全局字体（预留接口，供未来设置页调用）

    Args:
        app: QApplication 实例
        family: 字体族名，空字符串表示使用系统默认
        size: 字号
    """
    if family:
        font = QFont(family, size)
        app.setFont(font)
