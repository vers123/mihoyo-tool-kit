"""命令行界面：命令注册器 + 交互菜单。

本包仅导出注册器与菜单；命令定义位于 :mod:`mihoyo_toolkit.cli.commands`，
需由入口模块显式导入以完成注册（避免与 ``__main__`` 形成循环导入）。
"""

from __future__ import annotations

from .menu import Menu
from .registry import Command, CommandRegistry, registry

__all__ = ["Command", "CommandRegistry", "Menu", "registry"]
