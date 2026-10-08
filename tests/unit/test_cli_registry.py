"""cli.registry 单元测试。"""

from __future__ import annotations

import pytest

from mihoyo_toolkit.cli.registry import Command, CommandRegistry, registry


def test_register_returns_command() -> None:
    reg = CommandRegistry()

    @reg.register(key="a.b", label="标签", description="描述", group="分组", order=3)
    def handler() -> None:
        pass

    command = reg.get("a.b")
    assert isinstance(command, Command)
    assert command.key == "a.b"
    assert command.label == "标签"
    assert command.group == "分组"
    assert command.order == 3
    assert command.handler is handler


def test_duplicate_key_raises() -> None:
    reg = CommandRegistry()
    reg.register(key="x", label="", description="", group="g")(lambda: None)
    with pytest.raises(ValueError):
        reg.register(key="x", label="", description="", group="g")(lambda: None)


def test_get_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        CommandRegistry().get("missing")


def test_all_preserves_registration_order() -> None:
    reg = CommandRegistry()
    reg.register(key="a", label="", description="", group="g")(lambda: None)
    reg.register(key="b", label="", description="", group="g")(lambda: None)
    assert [c.key for c in reg.all()] == ["a", "b"]


def test_by_group_orders_within_group() -> None:
    reg = CommandRegistry()
    reg.register(key="a", label="", description="", group="G1", order=2)(lambda: None)
    reg.register(key="b", label="", description="", group="G1", order=1)(lambda: None)
    reg.register(key="c", label="", description="", group="G2", order=0)(lambda: None)

    groups = reg.by_group()
    assert list(groups) == ["G1", "G2"]
    assert [c.key for c in groups["G1"]] == ["b", "a"]
    assert [c.key for c in groups["G2"]] == ["c"]


def test_module_level_registry_singleton() -> None:
    assert isinstance(registry, CommandRegistry)
