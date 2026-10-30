"""字体加载（容错：字体文件缺失时静默回退到系统字体）。

主中文字体为思源黑体 CN（Source Han Sans CN），在 ``QApplication`` 创建后
注册并应用为全局字体；游戏字体仅用于「对应游戏」的导航项标题与页面标题。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .paths import get_font_dir

if TYPE_CHECKING:
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

#: 主中文字体族名
MAIN_FONT_FAMILY: str = "Source Han Sans CN"

#: 主中文字体文件（Regular / Bold，同一字体族），相对 resources/font
MAIN_FONT_FILES: tuple[str, ...] = (
    "SourceHanSansCN/SourceHanSansCN-Regular.otf",
    "SourceHanSansCN/SourceHanSansCN-Bold.otf",
)

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
FALLBACK_FAMILY: str = MAIN_FONT_FAMILY


def _register_font(relative: str) -> str:
    """把单个字体文件注册到 ``QFontDatabase``，返回族名（失败时为空串）。"""
    from PySide6.QtGui import QFontDatabase

    path = get_font_dir() / relative
    if not path.is_file():
        return ""
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id == -1:
        return ""
    families = QFontDatabase.applicationFontFamilies(font_id)
    return families[0] if families else ""


def load_main_font() -> str:
    """注册主中文字体（思源黑体 CN）并返回族名；字体缺失时返回空串。

    会注册 :data:`MAIN_FONT_FILES` 中的全部字重（Regular / Bold），
    返回值取自第一个成功注册的字体。
    """
    family = ""
    for relative in MAIN_FONT_FILES:
        current = _register_font(relative)
        if current and not family:
            family = current
    return family


def load_game_fonts() -> dict[str, str]:
    """把可用的游戏字体注册到 ``QFontDatabase``，返回 ``{key: family}``。

    必须在 ``QApplication`` 创建之后调用；任何缺失或加载失败的字体都会被跳过。
    """
    loaded: dict[str, str] = {}
    for key, relative in {**GAME_TITLE_FONTS, **GAME_BODY_FONTS}.items():
        family = _register_font(relative)
        if family:
            loaded[key] = family
    return loaded


def get_title_font(game_key: str, fonts: dict[str, str], size: int = 16) -> QFont:
    """获取指定游戏的标题字体；未加载时回退到 :data:`FALLBACK_FAMILY`。"""
    from PySide6.QtGui import QFont

    family = fonts.get(game_key, FALLBACK_FAMILY)
    return QFont(family, size, QFont.Weight.Bold)


def apply_app_font(app: QApplication, family: str = "", size: int = 0) -> None:
    """应用全局字体（``family`` 为空表示使用系统默认，不修改）。

    ``size`` 小于等于 0 时保留 Qt 当前默认字号，仅替换字体族。
    """
    if not family:
        return

    font = app.font()
    font.setFamily(family)
    if size > 0:
        font.setPointSize(size)
    app.setFont(font)


__all__ = [
    "FALLBACK_FAMILY",
    "GAME_BODY_FONTS",
    "GAME_TITLE_FONTS",
    "MAIN_FONT_FAMILY",
    "MAIN_FONT_FILES",
    "apply_app_font",
    "get_title_font",
    "load_game_fonts",
    "load_main_font",
]
