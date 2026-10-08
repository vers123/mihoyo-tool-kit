"""双模式入口：交互菜单 / 非交互参数 / GUI。

* ``mihoyo-toolkit``            → :func:`main`（无参数时进入交互菜单）
* ``mihoyo-toolkit-gui``        → :func:`gui_main`（等价 ``main(["--gui"])``）
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__
from .cli import Menu
from .core import Storage, get_path_manager, get_settings
from .exporters import export_news_excel, generate_json_feed, generate_rss_feed
from .scrapers import run_news
from .utils import (
    check_and_migrate,
    get_har_welcome_text,
    run_filter,
    setup_console_log,
    setup_logger,
)


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="mihoyo-toolkit",
        description="米游社工具箱 —— 米游社 / 微博 / 米哈游四站点新闻数据抓取与提取工具",
    )
    parser.add_argument("--gui", action="store_true", help="启动图形界面")
    parser.add_argument(
        "--fetch",
        choices=["genshin", "genshin_en", "zzz", "starrail", "all"],
        help="非交互抓取新闻（API 直连，不启动浏览器）",
    )
    parser.add_argument("--export-excel", action="store_true", help="导出新闻到 Excel")
    parser.add_argument(
        "--export-feed",
        choices=["rss", "json"],
        help="导出 RSS / JSON Feed",
    )
    parser.add_argument("--count", action="store_true", help="显示 SQLite 各游戏条数")
    parser.add_argument("--filter", action="store_true", help="运行 TXT 过滤")
    parser.add_argument("--migrate", action="store_true", help="运行数据迁移")
    parser.add_argument("--version", action="store_true", help="打印版本号")
    return parser


def _run_fetch(target: str) -> None:
    """执行新闻抓取：``all`` 时逐站点增量抓取。"""
    games = list(get_settings().sources.news.keys()) if target == "all" else [target]
    for game in games:
        new = run_news(game, incremental=True)
        print(f"[{game}] 新增 {new} 条")


def _run_count() -> None:
    """打印 SQLite 各游戏新闻条数。"""
    with Storage() as store:
        counts = store.count_all()
    if not counts:
        print("[提示] 数据库暂无新闻数据")
        return
    for game, count in counts.items():
        print(f"  {game}: {count}")
    print(f"  合计: {sum(counts.values())}")


def _dispatch(args: argparse.Namespace) -> int:
    """执行非交互动作。"""
    if args.version:
        print(f"米游社工具箱 v{__version__}")
        return 0

    if args.gui:
        from .gui import launch_gui  # 延迟导入：仅 GUI 模式需要 Qt 依赖

        launch_gui()
        return 0

    if args.fetch:
        _run_fetch(args.fetch)
        return 0

    if args.export_excel:
        path = export_news_excel()
        print(f"[完成] 已导出 Excel: {get_path_manager().relative(path)}")
        return 0

    if args.export_feed:
        path = generate_rss_feed() if args.export_feed == "rss" else generate_json_feed()
        print(f"[完成] 已导出 Feed: {get_path_manager().relative(path)}")
        return 0

    if args.count:
        _run_count()
        return 0

    if args.filter:
        run_filter()
        return 0

    if args.migrate:
        check_and_migrate()
        print("[完成] 数据迁移检查结束（详情见日志）")
        return 0

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """程序主入口，返回退出码。"""
    setup_console_log()
    setup_logger()
    get_path_manager().ensure_dirs()

    args = _build_parser().parse_args(argv)

    has_action = bool(
        args.version
        or args.gui
        or args.fetch
        or args.export_excel
        or args.export_feed
        or args.count
        or args.filter
        or args.migrate
    )
    if has_action:
        return _dispatch(args)

    # 无参数：展示 HAR 指引后进入交互菜单
    print(get_har_welcome_text())
    try:
        input("\n按回车键进入交互菜单...")
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return 0

    from .cli import commands  # noqa: F401  导入以完成命令注册

    Menu().run()
    return 0


def gui_main() -> None:
    """GUI 脚本入口（``[project.gui-scripts]``）。"""
    raise SystemExit(main(["--gui"]))


if __name__ == "__main__":
    raise SystemExit(main())
