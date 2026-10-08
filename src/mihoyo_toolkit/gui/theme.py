"""主题调色板与样式表（自动跟随系统深浅色）。

* :data:`LIGHT` / :data:`DARK` —— 两套语义化调色板；
* :func:`detect_system_dark` —— 读取系统色彩方案（Qt 6.5+ ``QStyleHints``）；
* :func:`apply_to_application` —— 一次性设置 Fusion 样式 + 调色板 + 样式表；
* :func:`current` —— 获取当前生效调色板（供日志着色等动态取色）。

界面颜色一律通过 :func:`current` 获取，不再使用静态常量，
以便系统主题切换后重新取到新配色。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtWidgets import QApplication


#: 左侧导航栏宽度（像素）
NAV_WIDTH: Final = 190

#: 导航项高度（像素）—— 显式指定，避免游戏字体度量差异导致行高不一致/文字重叠
NAV_ITEM_HEIGHT: Final = 34

#: 标题字号相对基准字号的增量
TITLE_OFFSET: Final = 4

#: 日志面板保留的最大行数
LOG_MAX_BLOCKS: Final = 5000


@dataclass(frozen=True, slots=True)
class Palette:
    """一套语义化界面配色。"""

    background: str
    surface: str
    border: str
    text: str
    text_muted: str
    primary: str
    success: str
    warning: str
    error: str


#: 浅色调色板
LIGHT: Final[Palette] = Palette(
    background="#f5f6f8",
    surface="#ffffff",
    border="#d0d4da",
    text="#1f2937",
    text_muted="#6b7280",
    primary="#2563eb",
    success="#059669",
    warning="#d97706",
    error="#dc2626",
)

#: 深色调色板
DARK: Final[Palette] = Palette(
    background="#1e1f22",
    surface="#2b2d31",
    border="#3d4149",
    text="#e6e8eb",
    text_muted="#9aa0a6",
    primary="#3b82f6",
    success="#34d399",
    warning="#fbbf24",
    error="#f87171",
)

#: 当前生效调色板（由 :func:`set_current` 更新）
_current: Palette = LIGHT


def set_current(palette: Palette) -> None:
    """设置当前生效调色板。"""
    global _current
    _current = palette


def current() -> Palette:
    """返回当前生效调色板。"""
    return _current


# ---------------------------------------------------------------------- #
#  系统主题探测
# ---------------------------------------------------------------------- #
def _detect_dark_from_registry() -> bool | None:
    """Windows 注册表回退：读取 ``AppsUseLightTheme``。"""
    import sys

    if sys.platform != "win32":  # pragma: no cover - 仅 Windows
        return None
    try:
        import winreg
    except ImportError:  # pragma: no cover
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
    except OSError:
        return None
    return value == 0


def detect_system_dark() -> bool:
    """判断系统是否处于深色模式。

    探测顺序（避免读取到本程序自己设置的调色板）：

    1. Qt 6.5+ 的 ``QStyleHints.colorScheme()``（跨平台官方接口）；
    2. Windows 注册表 ``AppsUseLightTheme``；
    3. 保守回退为浅色。
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    scheme_getter = getattr(QGuiApplication.styleHints(), "colorScheme", None)
    if scheme_getter is not None:
        scheme = scheme_getter()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False

    registry_dark = _detect_dark_from_registry()
    if registry_dark is not None:
        return registry_dark

    return False


def system_palette() -> Palette:
    """按系统色彩方案返回对应调色板。"""
    return DARK if detect_system_dark() else LIGHT


# ---------------------------------------------------------------------- #
#  Qt 调色板与样式表
# ---------------------------------------------------------------------- #
def build_palette(palette: Palette | None = None):
    """把 :class:`Palette` 转换为 ``QPalette``。"""
    from PySide6.QtGui import QColor, QPalette

    p = palette or _current
    qt_palette = QPalette()
    roles = QPalette.ColorRole

    qt_palette.setColor(roles.Window, QColor(p.background))
    qt_palette.setColor(roles.WindowText, QColor(p.text))
    qt_palette.setColor(roles.Base, QColor(p.surface))
    qt_palette.setColor(roles.AlternateBase, QColor(p.background))
    qt_palette.setColor(roles.Text, QColor(p.text))
    qt_palette.setColor(roles.Button, QColor(p.surface))
    qt_palette.setColor(roles.ButtonText, QColor(p.text))
    qt_palette.setColor(roles.ToolTipBase, QColor(p.surface))
    qt_palette.setColor(roles.ToolTipText, QColor(p.text))
    qt_palette.setColor(roles.Highlight, QColor(p.primary))
    qt_palette.setColor(roles.HighlightedText, QColor(p.surface))
    qt_palette.setColor(roles.PlaceholderText, QColor(p.text_muted))
    # 禁用态文字（Disabled 属于 ColorGroup，需单独指定）
    qt_palette.setColor(QPalette.ColorGroup.Disabled, roles.Text, QColor(p.text_muted))
    # 表头 / 视图标题栏背景（避免深色模式下表头仍为亮色）
    qt_palette.setColor(roles.Mid, QColor(p.border))
    qt_palette.setColor(roles.Shadow, QColor(p.border))
    qt_palette.setColor(roles.Light, QColor(p.surface))
    return qt_palette


def app_stylesheet(palette: Palette | None = None) -> str:
    """生成与调色板匹配的全局样式表。"""
    p = palette or _current
    return f"""
QListWidget#navList {{
    background: {p.surface};
    border: none;
    border-right: 1px solid {p.border};
    outline: none;
    padding: 6px 4px;
}}
QListWidget#navList::item {{
    padding: 0 10px;
    border-radius: 4px;
    color: {p.text};
}}
QListWidget#navList::item:hover {{
    background: {p.background};
}}
QListWidget#navList::item:selected {{
    background: {p.primary};
    color: {p.surface};
}}
QLabel#pageSubtitle {{
    color: {p.text_muted};
}}
QProgressBar {{
    border: 1px solid {p.border};
    border-radius: 3px;
    height: 16px;
    text-align: center;
    color: {p.text};
}}
QProgressBar::chunk {{
    background-color: {p.primary};
}}
"""


def apply_to_application(app: QApplication, palette: Palette | None = None) -> Palette:
    """对 ``QApplication`` 应用主题，返回生效的调色板。

    ``palette`` 为 ``None`` 时自动探测系统深浅色。
    """
    chosen = palette or system_palette()
    app.setStyle("Fusion")
    app.setPalette(build_palette(chosen))
    app.setStyleSheet(app_stylesheet(chosen))
    set_current(chosen)
    return chosen


# ---------------------------------------------------------------------- #
#  日志着色
# ---------------------------------------------------------------------- #
def _log_rules(p: Palette) -> tuple[tuple[tuple[str, ...], str], ...]:
    """日志着色规则：(关键词元组, 颜色)，按声明顺序匹配，命中即返回。"""
    return (
        (("[error]", "[fail", "失败", "错误"), p.error),
        (("[warn", "警告", "中断"), p.warning),
        (("[ok]", "[success", "完成", "已导出"), p.success),
        (("[start]", "[info]", "[filter]"), p.primary),
    )


def log_color(message: str, palette: Palette | None = None) -> str:
    """按消息内容返回日志文本颜色（未命中时返回默认正文色）。"""
    p = palette or _current
    lower = message.lower()
    for keywords, color in _log_rules(p):
        if any(keyword in lower for keyword in keywords):
            return color
    return p.text


__all__ = [
    "DARK",
    "LIGHT",
    "LOG_MAX_BLOCKS",
    "NAV_ITEM_HEIGHT",
    "NAV_WIDTH",
    "Palette",
    "TITLE_OFFSET",
    "app_stylesheet",
    "apply_to_application",
    "build_palette",
    "current",
    "detect_system_dark",
    "log_color",
    "set_current",
    "system_palette",
]
