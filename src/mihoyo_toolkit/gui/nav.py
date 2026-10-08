"""GUI 导航装配：由 CLI 命令注册表派生。

CLI 交互菜单与 GUI 共用同一份命令清单（:mod:`mihoyo_toolkit.cli.registry`，命令
定义在 :mod:`mihoyo_toolkit.cli.commands`）：

* 导航**标题**取注册表的分组名，**顺序**即注册顺序；
* 需要单独成页的命令（目前只有 ``export.filter``／TXT 过滤）以命令自身的
  ``label`` 作标题，沿用 v2.0 的界面划分；
* 装配时校验每条命令**恰好**被一个页面负责，缺漏或重复立即抛
  :class:`~mihoyo_toolkit.core.exceptions.GuiError`，避免新增命令后 GUI 静默
  缺少入口。

页面本身仍是各自实现（参数采集方式与 CLI 的交互提示不同），共享的是命令清单、
分组与顺序。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from ..cli.commands import registry as cli_registry
from ..cli.registry import CommandRegistry
from ..core.exceptions import GuiError
from .pages import (
    ExportPage,
    FilterPage,
    NewsPage,
    OtherPage,
    SystemPage,
    UserPostsPage,
    WeiboPage,
)
from .pages.base import BasePage

#: 页面工厂：无参可调用对象，返回页面实例
PageFactory = Callable[[], BasePage]

#: 注册表分组名 → 页面工厂（分组名必须与注册表一致）
_GROUP_FACTORIES: dict[str, PageFactory] = {
    "米游社用户": UserPostsPage,
    "原神新闻": partial(NewsPage, "genshin"),
    "原神英文版新闻": partial(NewsPage, "genshin_en"),
    "绝区零新闻": partial(NewsPage, "zzz"),
    "星穹铁道新闻": partial(NewsPage, "starrail"),
    "其他抓取": OtherPage,
    "微博": WeiboPage,
    "系统工具": SystemPage,
    "数据导出": ExportPage,
}

#: 需要单独成页的命令：命令 key → 页面工厂（标题取命令 label）
_SPLIT_COMMANDS: dict[str, PageFactory] = {
    "export.filter": FilterPage,
}


@dataclass(frozen=True)
class NavEntry:
    """一个导航项。

    Attributes:
        key: 命令 key 的命名空间前缀（如 ``genshin``），用于游戏字体查找等。
        title: 导航标题（分组名，或单独成页命令的 ``label``）。
        commands: 该页面负责的命令 key，顺序与注册表一致。
        factory: 创建页面的无参工厂。
    """

    key: str
    title: str
    commands: tuple[str, ...]
    factory: PageFactory


def build_nav(reg: CommandRegistry | None = None) -> list[NavEntry]:
    """按注册表分组顺序生成导航项。

    Args:
        reg: 命令注册表，默认使用 CLI 的全局注册表。

    Returns:
        导航项列表，其中命令 key 的并集恰好等于注册表全部命令。

    Raises:
        GuiError: 分组没有配置页面，或存在未被负责 / 被重复负责的命令。
    """
    registry = reg if reg is not None else cli_registry
    entries: list[NavEntry] = []

    for group, commands in registry.by_group().items():
        factory = _GROUP_FACTORIES.get(group)
        if factory is None:
            raise GuiError(
                f"GUI 未为命令分组「{group}」配置页面",
                detail="请在 mihoyo_toolkit.gui.nav._GROUP_FACTORIES 中登记",
            )

        # 同一分组内：单独成页的命令各自一项，其余合并为分组页
        split = [cmd for cmd in commands if cmd.key in _SPLIT_COMMANDS]
        main = [cmd for cmd in commands if cmd.key not in _SPLIT_COMMANDS]
        if main:
            entries.append(
                NavEntry(
                    key=_namespace(main[0].key),
                    title=group,
                    commands=tuple(cmd.key for cmd in main),
                    factory=factory,
                )
            )
        for cmd in split:
            entries.append(
                NavEntry(
                    key=_namespace(cmd.key),
                    title=cmd.label,
                    commands=(cmd.key,),
                    factory=_SPLIT_COMMANDS[cmd.key],
                )
            )

    _check_coverage(registry, entries)
    return entries


def _namespace(key: str) -> str:
    """命令 key 的命名空间前缀（``genshin.fetch`` → ``genshin``）。"""
    return key.split(".", 1)[0]


def _check_coverage(reg: CommandRegistry, entries: list[NavEntry]) -> None:
    """校验注册表中的命令恰好被一个页面负责。"""
    covered = [key for entry in entries for key in entry.commands]
    missing = [cmd.key for cmd in reg.all() if cmd.key not in covered]
    if missing:
        raise GuiError(
            "以下命令没有对应的 GUI 页面：" + "、".join(missing),
            detail="请在 mihoyo_toolkit.gui.nav 中补充 _GROUP_FACTORIES / _SPLIT_COMMANDS",
        )

    duplicates = sorted({key for key in covered if covered.count(key) > 1})
    if duplicates:
        raise GuiError(
            "以下命令被多个 GUI 页面重复负责：" + "、".join(duplicates),
            detail="同一个命令 key 只能出现在一个页面中",
        )


__all__ = ["NavEntry", "PageFactory", "build_nav"]
