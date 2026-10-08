"""cli.menu 单元测试（不进入阻塞主循环的耗时分支）。"""

from __future__ import annotations

from mihoyo_toolkit.cli.menu import Menu
from mihoyo_toolkit.cli.registry import CommandRegistry
from mihoyo_toolkit.core.exceptions import MihoyoError


def _registry(*specs) -> CommandRegistry:
    reg = CommandRegistry()
    for key, group, handler in specs:
        reg.register(key=key, label=key.upper(), description="", group=group)(handler)
    return reg


def test_ordered_flattens_groups() -> None:
    reg = _registry(("a", "G1", lambda: None), ("b", "G2", lambda: None))
    assert [c.key for c in Menu(reg)._ordered()] == ["a", "b"]


def test_render_prints_groups(capsys) -> None:
    reg = _registry(("a", "G1", lambda: None))
    menu = Menu(reg)
    menu._render(menu._ordered())
    out = capsys.readouterr().out
    assert "米游社工具箱" in out
    assert "A" in out
    assert "退出" in out


def test_clear_calls_os_system(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("mihoyo_toolkit.cli.menu.os.system", lambda cmd: calls.append(cmd))
    Menu._clear()
    assert calls


def test_execute_success(capsys) -> None:
    reg = CommandRegistry()
    reg.register(key="ok", label="", description="", group="g")(lambda: None)
    Menu(reg)._execute(reg.get("ok"))
    assert "[完成] 命令执行结束" in capsys.readouterr().out


def test_execute_mihoyo_error(capsys) -> None:
    reg = CommandRegistry()

    def handler() -> None:
        raise MihoyoError("出错了")

    reg.register(key="e", label="", description="", group="g")(handler)
    Menu(reg)._execute(reg.get("e"))
    assert "[错误] 出错了" in capsys.readouterr().out


def test_execute_keyboard_interrupt(capsys) -> None:
    reg = CommandRegistry()

    def handler() -> None:
        raise KeyboardInterrupt

    reg.register(key="k", label="", description="", group="g")(handler)
    Menu(reg)._execute(reg.get("k"))
    assert "操作被中断" in capsys.readouterr().out


def test_execute_generic_error(capsys) -> None:
    reg = CommandRegistry()

    def handler() -> None:
        raise ValueError("boom")

    reg.register(key="x", label="", description="", group="g")(handler)
    Menu(reg)._execute(reg.get("x"))
    assert "命令执行失败" in capsys.readouterr().out


def _patch_clear(monkeypatch) -> None:
    monkeypatch.setattr("mihoyo_toolkit.cli.menu.os.system", lambda cmd: None)


def test_run_exits_on_zero(monkeypatch, capsys) -> None:
    reg = _registry(("a", "g", lambda: None))
    _patch_clear(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *_: "0")
    Menu(reg).run()
    assert "再见" in capsys.readouterr().out


def test_run_invalid_then_execute_then_quit(monkeypatch, capsys) -> None:
    called: list[int] = []
    reg = _registry(("a", "g", lambda: called.append(1)))
    _patch_clear(monkeypatch)
    inputs = iter(["abc", "", "1", "", "0"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

    Menu(reg).run()

    assert called == [1]
    assert "无效输入" in capsys.readouterr().out


def test_run_out_of_range(monkeypatch, capsys) -> None:
    reg = _registry(("a", "g", lambda: None))
    _patch_clear(monkeypatch)
    inputs = iter(["9", "", "0"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

    Menu(reg).run()

    assert "序号超出范围" in capsys.readouterr().out


def test_run_eof_exits(monkeypatch, capsys) -> None:
    reg = _registry(("a", "g", lambda: None))
    _patch_clear(monkeypatch)

    def raise_eof(*_args) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    Menu(reg).run()
    assert "再见" in capsys.readouterr().out
