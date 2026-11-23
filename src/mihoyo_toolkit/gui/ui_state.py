"""GUI 本地状态持久化（主题偏好等）。

状态写在**工作区内**的 ``data/ui_state.json``，不写注册表 / 用户目录，
与「工作区外只读」的约定一致。写入走 :func:`mihoyo_toolkit.utils.fsio.atomic_write_text`，
读取失败或内容损坏时回退默认值（界面不应因状态文件损坏而无法启动）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.paths import get_path_manager
from ..utils.fsio import atomic_write_text
from ..utils.logger import get_module_logger
from . import theme

logger = get_module_logger("gui.ui_state")

#: 状态文件名（位于 ``data/`` 下）
STATE_FILENAME = "ui_state.json"


def state_path() -> Path:
    """状态文件路径（``data/ui_state.json``）。"""
    return get_path_manager().data / STATE_FILENAME


def load_state() -> dict[str, Any]:
    """读取状态；文件缺失或损坏时返回空字典。"""
    path = state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("读取界面状态失败，使用默认值: %s", exc)
        return {}
    return data if isinstance(data, dict) else {}


def load_theme_mode() -> theme.ThemeMode:
    """读取主题模式；缺失或非法时返回默认模式。"""
    value = load_state().get("theme")
    if isinstance(value, str) and value in theme.MODE_LABELS:
        return value
    return theme.DEFAULT_MODE


def save_theme_mode(mode: str) -> Path | None:
    """保存主题模式；失败只记录日志（不阻塞界面）。"""
    state = load_state()
    state["theme"] = theme.set_mode(mode)
    try:
        return atomic_write_text(state_path(), json.dumps(state, ensure_ascii=False, indent=2))
    except Exception as exc:  # pragma: no cover - 磁盘满/只读等环境问题
        logger.warning("保存界面状态失败: %s", exc)
        return None


__all__ = [
    "STATE_FILENAME",
    "load_state",
    "load_theme_mode",
    "save_theme_mode",
    "state_path",
]
