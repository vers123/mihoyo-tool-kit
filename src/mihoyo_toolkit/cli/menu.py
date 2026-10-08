"""交互式命令行菜单。

按 :data:`mihoyo_toolkit.cli.registry.registry` 中的分组渲染菜单，
编号全局连续递增，选择后执行对应命令的 handler。
"""

from __future__ import annotations

import os

from .. import __version__
from ..core.exceptions import MihoyoError
from ..utils import get_module_logger
from .registry import Command, CommandRegistry, registry

logger = get_module_logger("menu")


class Menu:
    """基于命令注册表的交互式菜单。"""

    def __init__(self, commands: CommandRegistry | None = None) -> None:
        self._registry = commands or registry

    # ------------------------------------------------------------------ #
    #  渲染
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clear() -> None:
        """清屏（跨平台）。"""
        os.system("cls" if os.name == "nt" else "clear")

    def _ordered(self) -> list[Command]:
        """按分组顺序展平命令，得到全局编号顺序。"""
        ordered: list[Command] = []
        for group in self._registry.by_group().values():
            ordered.extend(group)
        return ordered

    def _render(self, commands: list[Command]) -> None:
        """打印头部与分组菜单。"""
        print("=" * 60)
        print(f"  米游社工具箱 v{__version__}")
        print("  基于 API + Playwright 的数据抓取工具")
        print("=" * 60)

        counter = 1
        for group, items in self._registry.by_group().items():
            print(f"\n【{group}】")
            for command in items:
                print(f"  {counter:>2}. {command.label}")
                counter += 1
        print("\n   0. 退出")
        print("-" * 60)

    # ------------------------------------------------------------------ #
    #  执行
    # ------------------------------------------------------------------ #
    def _execute(self, command: Command) -> None:
        """执行命令并统一处理异常。"""
        logger.info("执行命令: %s (%s)", command.key, command.label)
        try:
            command.handler()
        except KeyboardInterrupt:
            print("\n[已取消] 操作被中断")
        except MihoyoError as exc:
            print(f"\n[错误] {exc}")
            logger.error("命令 %s 执行失败: %s", command.key, exc)
        except Exception as exc:  # 菜单需兜底，避免单条命令崩溃导致整体退出
            print(f"\n[错误] 命令执行失败: {exc}")
            logger.exception("命令 %s 异常", command.key)
        else:
            print("\n[完成] 命令执行结束")

    def run(self) -> None:
        """主循环。"""
        while True:
            self._clear()
            commands = self._ordered()
            self._render(commands)

            try:
                raw = input("请选择操作: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                return

            if raw in {"0", "q", "Q"}:
                print("再见！")
                return

            if not raw.isdigit():
                print("[提示] 无效输入，请输入菜单序号")
                input("\n按回车键继续...")
                continue

            index = int(raw) - 1
            if not 0 <= index < len(commands):
                print("[提示] 序号超出范围")
                input("\n按回车键继续...")
                continue

            self._execute(commands[index])
            try:
                input("\n按回车键继续...")
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                return


__all__ = ["Menu"]
