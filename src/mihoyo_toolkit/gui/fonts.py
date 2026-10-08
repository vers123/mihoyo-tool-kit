"""游戏字体加载（容错：字体文件缺失时静默回退到系统字体）。

字体用于「对应游戏」的导航项标题与页面标题；不改变全局字体。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .paths import get_font_dir

if TYPE_CHECKING:
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

#: game key -> resources/font 下的相对路径（标题字体）
GAME_TITLE_FONTS: dict[str, str] = {
    "genshin": "Genshin Impact/Teyvat-Black/ttf/TeyvatBlack-Regular.ttf",
    "starrail": "Star Rail/Star-Rail-Neue/ttf/StarRailNeue-Sans-Regular.ttf",
    "zzz": "ZenlessZoneZero/ZZZ-System/ttf/ZZZSystem-Regular.ttf",
}

#: 正文/备选游戏字体
GAME_BODY_FONTS: dict[str, str] = {
    "zzz_body": "ZenlessZoneZero/ZZZ-A/ttf/ZZZA-Regular.ttf",
}

#: 字体缺失时的回退族名
FALLBACK_FAMILY: str = "Microsoft YaHei"


def load_game_fonts() -> dict[str, str]:
    """把可用的游戏字体注册到 ``QFontDatabase``，返回 ``{key: family}``。

    必须在 ``QApplication`` 创建之后调用；任何缺失或加载失败的字体都会被跳过。
    """
    from PySide6.QtGui import QFontDatabase

    font_dir = get_font_dir()
    loaded: dict[str, str] = {}
    for key, relative in {**GAME_TITLE_FONTS, **GAME_BODY_FONTS}.items():
        path = font_dir / relative
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id == -1:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            loaded[key] = families[0]
    return loaded


def get_title_font(game_key: str, fonts: dict[str, str], size: int = 16) -> QFont:
    """获取指定游戏的标题字体；未加载时回退到 :data:`FALLBACK_FAMILY`。"""
    from PySide6.QtGui import QFont

    family = fonts.get(game_key, FALLBACK_FAMILY)
    return QFont(family, size, QFont.Weight.Bold)


def apply_app_font(app: QApplication, family: str = "", size: int = 12) -> None:
    """应用全局字体（``family`` 为空表示使用系统默认，不修改）。"""
    if not family:
        return

    from PySide6.QtGui import QFont

    app.setFont(QFont(family, size))


__all__ = [
    "FALLBACK_FAMILY",
    "GAME_BODY_FONTS",
    "GAME_TITLE_FONTS",
    "apply_app_font",
    "get_title_font",
    "load_game_fonts",
]
