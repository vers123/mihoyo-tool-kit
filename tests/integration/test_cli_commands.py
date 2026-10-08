"""CLI 命令注册与执行集成测试。"""

from __future__ import annotations

from pathlib import Path

import mihoyo_toolkit.cli.commands as commands
from mihoyo_toolkit.cli.commands import NEWS_GROUPS
from mihoyo_toolkit.cli.registry import registry

EXPECTED_COMMAND_COUNT = 43


def test_commands_are_registered() -> None:
    # 导入 commands 即完成注册；不得重复注册
    assert len(registry.all()) == EXPECTED_COMMAND_COUNT


def test_expected_keys_present() -> None:
    for key in (
        "user.fetch",
        "user.extract",
        "genshin.fetch",
        "genshin.fetch_incremental",
        "genshin.extract",
        "starrail.extract_incremental",
        "other.baike",
        "other.tutorial",
        "weibo.fetch",
        "system.backups",
        "system.info",
        "system.clean",
        "export.excel",
        "export.rss",
        "export.json",
        "export.filter",
    ):
        assert registry.get(key).key == key


def test_news_groups() -> None:
    assert NEWS_GROUPS == {
        "genshin": "原神新闻",
        "genshin_en": "原神英文版新闻",
        "zzz": "绝区零新闻",
        "starrail": "星穹铁道新闻",
    }


def test_grouping() -> None:
    groups = registry.by_group()
    assert "米游社用户" in groups
    assert "系统工具" in groups
    assert "数据导出" in groups
    # 组内按 order 排序
    orders = [c.order for c in groups["米游社用户"]]
    assert orders == sorted(orders)


def test_backup_target(tmp_home: Path) -> None:
    from mihoyo_toolkit.core.paths import get_path_manager

    paths = get_path_manager()
    assert commands._backup_target("toolkit.db") == paths.db
    assert commands._backup_target("posts.txt") == paths.results / "user" / "posts.txt"


def test_set_toml_value(tmp_home: Path) -> None:
    text = '[fetch]\nwait_seconds = 3.0  # 注释\n\n[sources.user]\nurl = "https://a"\n'
    updated, ok = commands._set_toml_value(text, "fetch", "wait_seconds", "5.0")
    assert ok is True
    assert "wait_seconds = 5.0  # 注释" in updated

    _, missing = commands._set_toml_value(text, "missing", "key", "1")
    assert missing is False


def test_playwright_version() -> None:
    assert isinstance(commands._playwright_version(), str)


def test_all_handlers_execute(monkeypatch, tmp_home: Path) -> None:
    calls: list[str] = []

    def noop(*_args, **_kwargs) -> None:
        calls.append("call")

    for name in (
        "run_user",
        "run_weibo",
        "run_baike",
        "run_custom",
        "run_model_download",
        "run_tutorial",
        "run_tutorial_batch",
        "run_news",
        "run_extract_posts",
        "run_extract_weibo",
        "run_extract_news",
        "run_extract_images",
        "run_extract_tutorial",
        "run_filter",
        "check_and_migrate",
    ):
        monkeypatch.setattr(commands, name, noop)

    monkeypatch.setattr(commands, "export_news_excel", lambda: tmp_home / "out.xlsx")
    monkeypatch.setattr(commands, "generate_rss_feed", lambda: tmp_home / "feed.xml")
    monkeypatch.setattr(commands, "generate_json_feed", lambda: tmp_home / "feed.json")
    monkeypatch.setattr("builtins.input", lambda *_: "")

    for command in registry.all():
        command.handler()

    # 31 个 handler 会调用被替换的底层函数：
    # 用户 4 + 新闻 16 + 其他 6 + 微博 4 + TXT 过滤 1（导出 3 个与 other.custom 不经过）
    assert len(calls) == 31


def test_other_custom_with_url(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        commands,
        "run_custom",
        lambda url, filename: captured.update(url=url, filename=filename),
    )
    inputs = iter(["https://example.com", "page.html"])
    monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

    registry.get("other.custom").handler()

    assert captured == {"url": "https://example.com", "filename": "page.html"}


def test_system_clean_cancelled(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda *_: "no")
    registry.get("system.clean").handler()
    assert "已取消清理" in capsys.readouterr().out


def test_system_migrate_cancelled(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    registry.get("system.migrate").handler()
    assert "已取消数据迁移" in capsys.readouterr().out


def test_system_restore_no_backups(monkeypatch, capsys) -> None:
    registry.get("system.restore").handler()
    assert "未找到任何可恢复的备份" in capsys.readouterr().out


def test_system_config_show(capsys, settings) -> None:
    registry.get("system.config_show").handler()
    out = capsys.readouterr().out
    assert "当前配置" in out
    assert settings.sources.user.url in out


def test_system_info(capsys) -> None:
    registry.get("system.info").handler()
    assert "系统信息" in capsys.readouterr().out


def test_system_config_reload(capsys) -> None:
    registry.get("system.config_reload").handler()
    assert "配置已重新加载" in capsys.readouterr().out


def test_export_handlers(monkeypatch, capsys) -> None:
    monkeypatch.setattr(commands, "export_news_excel", lambda: Path("x.xlsx"))
    registry.get("export.excel").handler()
    monkeypatch.setattr(commands, "generate_rss_feed", lambda: Path("x.xml"))
    registry.get("export.rss").handler()
    monkeypatch.setattr(commands, "generate_json_feed", lambda: Path("x.json"))
    registry.get("export.json").handler()
    out = capsys.readouterr().out
    assert "已导出 Excel" in out
    assert "已导出 RSS" in out
    assert "已导出 JSON" in out


def test_system_backups_empty(capsys) -> None:
    registry.get("system.backups").handler()
    assert "备份" in capsys.readouterr().out
