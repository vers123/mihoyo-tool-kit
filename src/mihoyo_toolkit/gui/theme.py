"""主题令牌、三态主题与全局样式表（官网风）。

视觉参考 https://www.mihoyo.com/ ：

* 主色 ``#3778e5``，正文 ``#3d424d`` / 标题 ``#242933``，辅助 ``#676b73``；
* 页面底 ``#f8f9fb``，卡片/面板 ``#ffffff``，分割线 ``#e6e7eb``；
* 小圆角（5px）、导航选中胶囊（10px）、克制的阴影与留白。

三种模式：``auto``（跟随系统）/ ``light`` / ``dark``；:func:`apply_mode` 会记住
当前模式并返回生效的调色板，:func:`current_mode` 供界面展示选中态。
界面颜色统一通过 :func:`current` 获取，以便主题切换后重新取色。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:  # pragma: no cover
    from PySide6.QtWidgets import QApplication

#: 主题模式
ThemeMode = Literal["auto", "light", "dark"]

#: 模式 → 中文标签（顺序即界面上的分段顺序）
MODE_LABELS: Final[dict[ThemeMode, str]] = {
    "auto": "跟随系统",
    "light": "浅色",
    "dark": "深色",
}

#: 默认模式：跟随系统
DEFAULT_MODE: Final[ThemeMode] = "auto"

#: 左侧导航栏宽度（像素）
NAV_WIDTH: Final = 190

#: 导航项高度（像素）—— 显式指定，避免游戏字体度量差异导致行高不一致/文字重叠
NAV_ITEM_HEIGHT: Final = 38

#: 标题字号相对基准字号的增量
TITLE_OFFSET: Final = 5

#: 日志面板保留的最大行数
LOG_MAX_BLOCKS: Final = 5000

#: 基础圆角（按钮 / 输入框 / 卡片）
RADIUS: Final = 5

#: 导航选中胶囊 / 卡片圆角
RADIUS_PILL: Final = 10

#: 卡片内边距与卡片间距
CARD_PADDING: Final = 18
CARD_SPACING: Final = 14


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
    # ---- 官网风扩展令牌（均有默认值，保持向后兼容）----
    #: 次级面板底色（表头、悬停行、分组底）
    surface_alt: str = "#f2f4f7"
    #: 次级正文色（比 text 略浅）
    text_secondary: str = "#3d424d"
    #: 强分割线（输入框/按钮描边）
    border_strong: str = "#dee1e6"
    #: 主色悬停 / 按下 / 浅底
    primary_hover: str = "#2f6ad0"
    primary_pressed: str = "#285cb8"
    primary_soft: str = "#e8f0fd"
    #: 品牌栏底色
    brand_background: str = "#ffffff"


#: 浅色调色板（对齐 mihoyo.com）
LIGHT: Final[Palette] = Palette(
    background="#f8f9fb",
    surface="#ffffff",
    border="#e6e7eb",
    text="#242933",
    text_muted="#676b73",
    primary="#3778e5",
    success="#01a99a",
    warning="#d97706",
    error="#e04b4b",
    surface_alt="#f2f4f7",
    text_secondary="#3d424d",
    border_strong="#dee1e6",
    primary_hover="#2f6ad0",
    primary_pressed="#285cb8",
    primary_soft="#e8f0fd",
    brand_background="#ffffff",
)

#: 深色调色板（沿用同一套语义，底色取官网深色区）
DARK: Final[Palette] = Palette(
    background="#1b1d22",
    surface="#242933",
    border="#3d424d",
    text="#eef0f3",
    text_muted="#99a3af",
    primary="#4b8bf0",
    success="#34d399",
    warning="#fbbf24",
    error="#f87171",
    surface_alt="#2c313c",
    text_secondary="#d7dbe0",
    border_strong="#4a4f5a",
    primary_hover="#6ba1f5",
    primary_pressed="#3a75d4",
    primary_soft="#2b3b57",
    brand_background="#20242c",
)

#: 当前生效调色板（由 :func:`set_current` 更新）
_current: Palette = LIGHT

#: 当前主题模式（由 :func:`set_mode` 更新）
_current_mode: ThemeMode = DEFAULT_MODE


def set_current(palette: Palette) -> None:
    """设置当前生效调色板。"""
    global _current
    _current = palette


def current() -> Palette:
    """返回当前生效调色板。"""
    return _current


def current_mode() -> ThemeMode:
    """返回当前主题模式（``auto`` / ``light`` / ``dark``）。"""
    return _current_mode


def set_mode(mode: str) -> ThemeMode:
    """设置主题模式并返回规范化后的值；非法值回退到 ``auto``。"""
    global _current_mode
    normalized: ThemeMode = mode if mode in MODE_LABELS else DEFAULT_MODE
    _current_mode = normalized
    return _current_mode


# ---------------------------------------------------------------------- #
#  系统主题探测
# ---------------------------------------------------------------------- #
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


def resolve_mode(mode: str | None = None) -> Palette:
    """按模式解析出调色板；``auto`` / ``None`` 时跟随系统。"""
    effective = mode if mode in MODE_LABELS else current_mode()
    if effective == "light":
        return LIGHT
    if effective == "dark":
        return DARK
    return system_palette()


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
    qt_palette.setColor(roles.AlternateBase, QColor(p.surface_alt))
    qt_palette.setColor(roles.Text, QColor(p.text))
    qt_palette.setColor(roles.Button, QColor(p.surface))
    qt_palette.setColor(roles.ButtonText, QColor(p.text))
    qt_palette.setColor(roles.ToolTipBase, QColor(p.surface))
    qt_palette.setColor(roles.ToolTipText, QColor(p.text))
    qt_palette.setColor(roles.Highlight, QColor(p.primary))
    qt_palette.setColor(roles.HighlightedText, QColor("#ffffff"))
    qt_palette.setColor(roles.PlaceholderText, QColor(p.text_muted))
    # 禁用态文字（Disabled 属于 ColorGroup，需单独指定）
    qt_palette.setColor(QPalette.ColorGroup.Disabled, roles.Text, QColor(p.text_muted))
    qt_palette.setColor(QPalette.ColorGroup.Disabled, roles.ButtonText, QColor(p.text_muted))
    # 表头 / 视图标题栏背景（避免深色模式下表头仍为亮色）
    qt_palette.setColor(roles.Mid, QColor(p.border))
    qt_palette.setColor(roles.Shadow, QColor(p.border))
    qt_palette.setColor(roles.Light, QColor(p.surface))
    return qt_palette


def app_stylesheet(palette: Palette | None = None) -> str:
    """生成与调色板匹配的全局样式表（官网风）。"""
    p = palette or _current
    return f"""
/* ---------- 基础 ---------- */
QWidget {{
    font-size: 13px;
}}
QMainWindow, QWidget#pageRoot {{
    background: {p.background};
}}
QToolTip {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    padding: 6px 8px;
}}

/* ---------- 顶部品牌栏 ---------- */
QFrame#brandBar {{
    background: {p.brand_background};
    border: none;
    border-bottom: 1px solid {p.border};
}}
QLabel#brandTitle {{
    color: {p.text};
    font-size: 16px;
    font-weight: 600;
}}
QLabel#brandVersion {{
    color: {p.text_muted};
    font-size: 12px;
}}
QToolButton#themeSegment {{
    color: {p.text_muted};
    background: transparent;
    border: 1px solid transparent;
    border-radius: {RADIUS_PILL}px;
    padding: 5px 12px;
    font-size: 12px;
}}
QToolButton#themeSegment:hover {{
    color: {p.primary};
    background: {p.surface_alt};
}}
QToolButton#themeSegment:checked {{
    color: {p.primary};
    background: {p.primary_soft};
    border: 1px solid {p.primary};
}}

/* ---------- 左侧导航 ---------- */
QListWidget#navList {{
    background: {p.surface};
    border: none;
    border-right: 1px solid {p.border};
    outline: none;
    padding: 10px 8px;
}}
QListWidget#navList::item {{
    padding: 0 12px;
    margin: 2px 0;
    border-radius: {RADIUS_PILL}px;
    color: {p.text_secondary};
}}
QListWidget#navList::item:hover {{
    background: {p.surface_alt};
    color: {p.primary};
}}
QListWidget#navList::item:selected {{
    background: {p.primary_soft};
    color: {p.primary};
    font-weight: 600;
}}

/* ---------- 内容区 ---------- */
QLabel#pageTitle {{
    color: {p.text};
    font-weight: 600;
}}
QLabel#pageSubtitle {{
    color: {p.text_muted};
}}
QFrame#pageHeaderDivider {{
    background: {p.border};
    border: none;
    max-height: 1px;
}}

/* ---------- 卡片 ---------- */
QFrame#homeCard {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS_PILL}px;
}}
QFrame#homeCard:hover {{
    border: 1px solid {p.primary};
    background: {p.surface};
}}
QLabel#cardTitle {{
    color: {p.text};
    font-size: 15px;
    font-weight: 600;
}}
QLabel#cardDesc {{
    color: {p.text_muted};
}}
QLabel#cardCount {{
    color: {p.primary};
    background: {p.primary_soft};
    border-radius: {RADIUS_PILL}px;
    padding: 2px 8px;
    font-size: 11px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS}px;
    padding: 6px 14px;
    min-height: 18px;
}}
QPushButton:hover {{
    color: {p.primary};
    border-color: {p.primary};
    background: {p.primary_soft};
}}
QPushButton:pressed {{
    background: {p.primary_soft};
    border-color: {p.primary_pressed};
}}
QPushButton:disabled {{
    color: {p.text_muted};
    border-color: {p.border};
    background: {p.surface_alt};
}}
QPushButton[variant="primary"] {{
    background: {p.primary};
    color: #ffffff;
    border: 1px solid {p.primary};
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{
    background: {p.primary_hover};
    border-color: {p.primary_hover};
    color: #ffffff;
}}
QPushButton[variant="primary"]:pressed {{
    background: {p.primary_pressed};
    border-color: {p.primary_pressed};
}}
QPushButton[variant="primary"]:disabled {{
    background: {p.border};
    border-color: {p.border};
    color: {p.text_muted};
}}

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS}px;
    padding: 5px 8px;
    selection-background-color: {p.primary};
    selection-color: #ffffff;
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTextBrowser:focus {{
    border: 1px solid {p.primary};
}}
QLineEdit:disabled, QComboBox:disabled, QPlainTextEdit:disabled {{
    color: {p.text_muted};
    background: {p.surface_alt};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
    selection-background-color: {p.primary_soft};
    selection-color: {p.primary};
    outline: none;
}}

/* ---------- 分组框 ---------- */
QGroupBox {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS_PILL}px;
    margin-top: 14px;
    padding: {CARD_PADDING - 6}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {p.text_secondary};
    font-weight: 600;
}}

/* ---------- 表格 ---------- */
QTableView {{
    background: {p.surface};
    alternate-background-color: {p.background};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    gridline-color: {p.border};
    selection-background-color: {p.primary_soft};
    selection-color: {p.text};
    outline: none;
}}
QHeaderView::section {{
    background: {p.surface_alt};
    color: {p.text_secondary};
    border: none;
    border-bottom: 1px solid {p.border};
    border-right: 1px solid {p.border};
    padding: 6px 8px;
    font-weight: 600;
}}
QTableView QTableCornerButton::section {{
    background: {p.surface_alt};
    border: none;
}}

/* ---------- 日志区 ---------- */
QFrame#logPanel {{
    background: {p.surface};
    border: none;
    border-top: 1px solid {p.border};
}}
QLabel#logTitle {{
    color: {p.text_muted};
    font-size: 12px;
    font-weight: 600;
}}
QPlainTextEdit#logViewer {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    padding: 6px 8px;
    color: {p.text_secondary};
}}

/* ---------- 进度条 ---------- */
QProgressBar {{
    background: {p.surface_alt};
    border: none;
    border-radius: 3px;
    height: 8px;
    text-align: center;
    color: {p.text_secondary};
}}
QProgressBar::chunk {{
    background-color: {p.primary};
    border-radius: 3px;
}}

/* ---------- 分隔条 / 状态栏 / 滚动条 ---------- */
QSplitter::handle {{
    background: {p.border};
    height: 1px;
    width: 1px;
}}
QStatusBar {{
    background: {p.brand_background};
    color: {p.text_muted};
    border-top: 1px solid {p.border};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p.border_strong};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p.text_muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {p.border_strong};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---------- 对话框 ---------- */
QDialog, QMessageBox {{
    background: {p.background};
}}
QDialog QLabel, QMessageBox QLabel {{
    color: {p.text};
}}
"""


def apply_to_application(app: QApplication, palette: Palette | None = None) -> Palette:
    """对 ``QApplication`` 应用主题，返回生效的调色板。

    ``palette`` 为 ``None`` 时按当前模式解析（``auto`` 跟随系统）。
    """
    chosen = palette or resolve_mode()
    app.setStyle("Fusion")
    app.setPalette(build_palette(chosen))
    app.setStyleSheet(app_stylesheet(chosen))
    set_current(chosen)
    return chosen


def apply_mode(app: QApplication, mode: str | None = None) -> Palette:
    """切换主题模式并立即应用到 ``QApplication``，返回生效调色板。"""
    set_mode(mode if mode is not None else current_mode())
    return apply_to_application(app, resolve_mode())


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
    return p.text_secondary


__all__ = [
    "CARD_PADDING",
    "CARD_SPACING",
    "DARK",
    "DEFAULT_MODE",
    "LIGHT",
    "LOG_MAX_BLOCKS",
    "MODE_LABELS",
    "NAV_ITEM_HEIGHT",
    "NAV_WIDTH",
    "Palette",
    "RADIUS",
    "RADIUS_PILL",
    "TITLE_OFFSET",
    "ThemeMode",
    "app_stylesheet",
    "apply_mode",
    "apply_to_application",
    "build_palette",
    "current",
    "current_mode",
    "detect_system_dark",
    "log_color",
    "resolve_mode",
    "set_current",
    "set_mode",
    "system_palette",
]
