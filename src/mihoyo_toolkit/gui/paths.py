"""GUI 资源路径解析（全部容错：缺失资源返回 ``None``，不抛异常）。

资源目录约定（由 :class:`~mihoyo_toolkit.core.paths.PathManager` 提供）：

* 图标 ``resources/icon/``（``app.ico`` / ``app.png``）
* 字体 ``resources/font/``
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..core import get_path_manager

if TYPE_CHECKING:
    from PySide6.QtGui import QIcon

#: 应用图标候选文件名（按优先级）
_APP_ICON_CANDIDATES: tuple[str, ...] = ("app.ico", "app.png")


def resource_path(*parts: str) -> Path:
    """拼接 ``resources`` 目录下的路径（不校验存在性）。"""
    return get_path_manager().resources.joinpath(*parts)


def get_icon_dir() -> Path:
    """图标目录。"""
    return get_path_manager().icons


def get_font_dir() -> Path:
    """字体目录。"""
    return get_path_manager().fonts


def get_icon_path(name: str) -> Path | None:
    """返回存在的图标文件路径；不存在时返回 ``None``。"""
    path = get_icon_dir() / name
    return path if path.is_file() else None


def get_app_icon_path() -> Path | None:
    """解析应用图标路径；全部候选缺失时返回 ``None``。"""
    for name in _APP_ICON_CANDIDATES:
        path = get_icon_path(name)
        if path is not None:
            return path
    return None


def load_app_icon() -> QIcon | None:
    """加载应用图标；文件缺失或加载失败时返回 ``None``。"""
    path = get_app_icon_path()
    if path is None:
        return None

    from PySide6.QtGui import QIcon

    icon = QIcon(str(path))
    return None if icon.isNull() else icon


__all__ = [
    "get_app_icon_path",
    "get_font_dir",
    "get_icon_dir",
    "get_icon_path",
    "load_app_icon",
    "resource_path",
]
