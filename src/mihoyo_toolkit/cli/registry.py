"""装饰器式命令注册器。

CLI 交互菜单与 GUI 共用同一份命令清单：命令以稳定 ``key`` 标识，按 ``group``
聚合展示，组内按 ``order`` 排序，组间顺序遵循首次注册顺序。

用法::

    from mihoyo_toolkit.cli.registry import registry

    @registry.register(
        key="user.fetch",
        label="抓取用户发帖主页",
        description="抓取米游社用户发帖主页并落库",
        group="米游社用户",
        order=0,
    )
    def user_fetch() -> None:
        ...
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

#: 命令处理器：无参、无返回值
Handler = Callable[[], None]
F = TypeVar("F", bound=Callable[..., object])


@dataclass(slots=True)
class Command:
    """一条可执行命令。"""

    #: 稳定标识（如 ``user.fetch``）
    key: str
    #: 中文菜单标题
    label: str
    #: 功能说明
    description: str
    #: 分组名（如 ``米游社用户``）
    group: str
    #: 实际执行体
    handler: Handler
    #: 组内排序（越小越靠前）
    order: int = 0


class CommandRegistry:
    """命令注册表（单例由模块级 ``registry`` 提供）。"""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(
        self,
        *,
        key: str,
        label: str,
        description: str,
        group: str,
        order: int = 0,
    ) -> Callable[[F], F]:
        """注册命令的装饰器工厂（重复 ``key`` 抛 :class:`ValueError`）。"""

        def decorator(func: F) -> F:
            if key in self._commands:
                raise ValueError(f"命令已注册: {key}")
            self._commands[key] = Command(
                key=key,
                label=label,
                description=description,
                group=group,
                handler=func,  # type: ignore[arg-type]
                order=order,
            )
            return func

        return decorator

    def get(self, key: str) -> Command:
        """按 key 获取命令，未注册时抛 :class:`KeyError`。"""
        try:
            return self._commands[key]
        except KeyError as exc:
            raise KeyError(f"未注册的命令: {key}") from exc

    def all(self) -> list[Command]:
        """返回全部命令（保持注册顺序）。"""
        return list(self._commands.values())

    def by_group(self) -> dict[str, list[Command]]:
        """按分组聚合，组内按 ``order`` 排序；组顺序为首次注册顺序。"""
        groups: dict[str, list[Command]] = {}
        for command in self._commands.values():
            groups.setdefault(command.group, []).append(command)
        for commands in groups.values():
            commands.sort(key=lambda command: command.order)
        return groups


#: 模块级单例
registry = CommandRegistry()


__all__ = ["Command", "CommandRegistry", "registry"]
