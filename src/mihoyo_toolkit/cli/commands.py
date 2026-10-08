"""CLI 命令定义（装饰器注册）。

每个命令对应交互菜单中的一项，同时也是 GUI 可复用的动作清单。
分组名与命令 key 均保持稳定，供上层（菜单 / 图形界面）按需编排。
"""

from __future__ import annotations

import importlib.metadata as metadata
import os
import platform
import re
import shutil
import sys
import tomllib
from pathlib import Path

from .. import __version__
from ..core import Storage, get_path_manager, get_settings, reload_settings
from ..exporters import export_news_excel, generate_json_feed, generate_rss_feed
from ..extractors import (
    run_extract_images,
    run_extract_news,
    run_extract_posts,
    run_extract_tutorial,
    run_extract_weibo,
)
from ..scrapers import (
    run_baike,
    run_custom,
    run_model_download,
    run_news,
    run_tutorial,
    run_tutorial_batch,
    run_user,
    run_weibo,
)
from ..utils import (
    BackupInfo,
    backup_manager,
    check_and_migrate,
    get_module_logger,
    log_function_call,
    run_filter,
)
from .registry import registry

logger = get_module_logger("commands")


# ====================================================================== #
#  米游社用户
# ====================================================================== #
@registry.register(
    key="user.fetch",
    label="抓取用户发帖主页",
    description="抓取米游社用户发帖主页并落库",
    group="米游社用户",
    order=0,
)
@log_function_call
def user_fetch() -> None:
    """抓取用户发帖主页（全量）。"""
    run_user(incremental=False)


@registry.register(
    key="user.fetch_incremental",
    label="增量抓取用户发帖",
    description="仅抓取新发帖，遇到已存在记录提前终止",
    group="米游社用户",
    order=1,
)
@log_function_call
def user_fetch_incremental() -> None:
    """抓取用户发帖主页（增量）。"""
    run_user(incremental=True)


@registry.register(
    key="user.extract",
    label="提取用户发帖时间",
    description="从数据库导出用户发帖时间到 TXT",
    group="米游社用户",
    order=2,
)
@log_function_call
def user_extract() -> None:
    """提取用户发帖时间（全量）。"""
    run_extract_posts(incremental=False)


@registry.register(
    key="user.extract_incremental",
    label="增量提取用户发帖",
    description="增量导出用户发帖时间到 TXT",
    group="米游社用户",
    order=3,
)
@log_function_call
def user_extract_incremental() -> None:
    """提取用户发帖时间（增量）。"""
    run_extract_posts(incremental=True)


# ====================================================================== #
#  四站点新闻（原神 / 原神英文版 / 绝区零 / 星穹铁道）
# ====================================================================== #
#: game key → 分组名
NEWS_GROUPS: dict[str, str] = {
    "genshin": "原神新闻",
    "genshin_en": "原神英文版新闻",
    "zzz": "绝区零新闻",
    "starrail": "星穹铁道新闻",
}


def _register_news_commands(game: str, group: str) -> None:
    """为单个新闻站点注册 4 条命令（抓取 / 增量抓取 / 提取 / 增量提取）。"""

    @registry.register(
        key=f"{game}.fetch",
        label="抓取新闻页面",
        description=f"抓取{group}页面并落库",
        group=group,
        order=0,
    )
    @log_function_call
    def _fetch() -> None:
        run_news(game, incremental=False)

    @registry.register(
        key=f"{game}.fetch_incremental",
        label="增量抓取新闻",
        description=f"增量抓取{group}并落库",
        group=group,
        order=1,
    )
    @log_function_call
    def _fetch_incremental() -> None:
        run_news(game, incremental=True)

    @registry.register(
        key=f"{game}.extract",
        label="提取新闻数据",
        description=f"导出{group}数据为 TXT",
        group=group,
        order=2,
    )
    @log_function_call
    def _extract() -> None:
        run_extract_news(game, incremental=False)

    @registry.register(
        key=f"{game}.extract_incremental",
        label="增量提取新闻",
        description=f"增量导出{group}数据为 TXT",
        group=group,
        order=3,
    )
    @log_function_call
    def _extract_incremental() -> None:
        run_extract_news(game, incremental=True)


for _game, _group in NEWS_GROUPS.items():
    _register_news_commands(_game, _group)


# ====================================================================== #
#  其他抓取
# ====================================================================== #
#: 教程详情页默认 ID
DEFAULT_TUTORIAL_ID = "mh4imrrhzdzi"
#: 教程目录索引页默认 ID
DEFAULT_INDEX_ID = "mhs2w008wf14"
#: 语言选项（1 = 默认，不追加 lang 参数）
LANG_CHOICES: dict[str, str | None] = {"1": None, "2": "zh-cn", "3": "en-us"}


def _prompt(label: str, default: str) -> str:
    """读取一行输入，空输入返回默认值。"""
    raw = input(f"{label} [默认 {default}]: ").strip()
    return raw or default


def _prompt_tutorial_id() -> str:
    """询问教程 ID。"""
    return _prompt("请输入教程ID", DEFAULT_TUTORIAL_ID)


def _prompt_lang() -> str | None:
    """询问语言，返回 lang 或 None。"""
    raw = input("请选择语言 (1=默认 / 2=zh-cn / 3=en-us) [默认 1]: ").strip()
    return LANG_CHOICES.get(raw or "1")


@registry.register(
    key="other.baike",
    label="抓取角色图鉴页面",
    description="抓取米游社角色图鉴页面并落库",
    group="其他抓取",
    order=0,
)
@log_function_call
def other_baike() -> None:
    """抓取角色图鉴页面。"""
    run_baike()


@registry.register(
    key="other.tutorial",
    label="抓取单个教程页面",
    description="抓取指定教程详情页并落库角色数据",
    group="其他抓取",
    order=1,
)
@log_function_call
def other_tutorial() -> None:
    """抓取单个教程页面。"""
    tutorial_id = _prompt_tutorial_id()
    lang = _prompt_lang()
    run_tutorial(tutorial_id, lang)


@registry.register(
    key="other.tutorial_batch",
    label="批量抓取教程目录",
    description="从教程目录页提取链接并批量抓取",
    group="其他抓取",
    order=2,
)
@log_function_call
def other_tutorial_batch() -> None:
    """批量抓取教程目录。"""
    index_id = _prompt("请输入教程目录索引页ID", DEFAULT_INDEX_ID)
    lang = _prompt_lang()
    run_tutorial_batch(index_id, lang)


@registry.register(
    key="other.extract_tutorial",
    label="提取教程数据",
    description="解析教程 HTML 并导出角色数据",
    group="其他抓取",
    order=3,
)
@log_function_call
def other_extract_tutorial() -> None:
    """提取教程数据。"""
    tutorial_id = _prompt_tutorial_id()
    lang = _prompt_lang()
    run_extract_tutorial(tutorial_id, lang)


@registry.register(
    key="other.images",
    label="提取图鉴图片链接",
    description="从图鉴 HTML 提取图片链接并落库",
    group="其他抓取",
    order=4,
)
@log_function_call
def other_images() -> None:
    """提取图鉴图片链接。"""
    run_extract_images()


@registry.register(
    key="other.custom",
    label="抓取自定义网站",
    description="抓取任意 URL 并保存 HTML",
    group="其他抓取",
    order=5,
)
@log_function_call
def other_custom() -> None:
    """抓取自定义网站。"""
    url = input("请输入要抓取的URL: ").strip()
    if not url:
        print("[取消] 未提供URL")
        return
    filename = _prompt("请输入输出文件名", "custom_page.html")
    run_custom(url, filename)


@registry.register(
    key="other.model_download",
    label="模型下载",
    description="下载角色模型资源",
    group="其他抓取",
    order=6,
)
@log_function_call
def other_model_download() -> None:
    """下载角色模型。"""
    run_model_download()


# ====================================================================== #
#  微博
# ====================================================================== #
@registry.register(
    key="weibo.fetch",
    label="抓取微博用户主页",
    description="抓取微博用户主页并落库",
    group="微博",
    order=0,
)
@log_function_call
def weibo_fetch() -> None:
    """抓取微博用户主页（全量）。"""
    run_weibo(incremental=False)


@registry.register(
    key="weibo.fetch_incremental",
    label="增量抓取微博",
    description="仅抓取新微博，遇到已存在记录提前终止",
    group="微博",
    order=1,
)
@log_function_call
def weibo_fetch_incremental() -> None:
    """抓取微博用户主页（增量）。"""
    run_weibo(incremental=True)


@registry.register(
    key="weibo.extract",
    label="提取微博数据",
    description="从数据库导出微博数据到 TXT",
    group="微博",
    order=2,
)
@log_function_call
def weibo_extract() -> None:
    """提取微博数据（全量）。"""
    run_extract_weibo(incremental=False)


@registry.register(
    key="weibo.extract_incremental",
    label="增量提取微博数据",
    description="增量导出微博数据到 TXT",
    group="微博",
    order=3,
)
@log_function_call
def weibo_extract_incremental() -> None:
    """提取微博数据（增量）。"""
    run_extract_weibo(incremental=True)


# ====================================================================== #
#  系统工具
# ====================================================================== #
#: 参与备份/恢复的源文件（``backup_manager.list_backups`` 的查询名）
BACKUP_SOURCES: tuple[str, ...] = (
    "toolkit.db",
    "posts.txt",
    "weibo.txt",
    "genshin_news.txt",
)

#: 清理缓存时跳过的目录
PROTECTED_DIRS: frozenset[str] = frozenset(
    {".venv", ".git", "browser", "data", "logs", "har", "node_modules"}
)

#: 清理缓存时一并删除的构建目录
BUILD_DIRS: tuple[str, ...] = ("build", "dist", ".pytest_cache")


def _backup_target(name: str) -> Path:
    """备份源文件名 → 恢复目标路径。"""
    paths = get_path_manager()
    if name.endswith(".db"):
        return paths.db
    return paths.results / name


def _playwright_version() -> str:
    """获取 Playwright 版本号，未安装时返回提示文本。"""
    try:
        return metadata.version("playwright")
    except metadata.PackageNotFoundError:
        return "未安装"


def _set_toml_value(text: str, section: str, key: str, rendered: str) -> tuple[str, bool]:
    """在 TOML 文本中按 ``[section]`` 定位并替换 ``key = value`` 的值。

    Returns:
        ``(新文本, 是否替换成功)``。保留行内注释与结尾换行。
    """
    trailing = "\n" if text.endswith("\n") else ""
    lines = text.splitlines()
    current = ""
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)(.+?)(\s+#.*)?$")
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped.strip("[]").strip()
            continue
        if current != section:
            continue
        match = pattern.match(line.strip())
        if match:
            lines[index] = f"{match.group(1)}{rendered}{match.group(3) or ''}"
            return "\n".join(lines) + trailing, True
    return text, False


@registry.register(
    key="system.backups",
    label="查看备份文件",
    description="列出各数据源的备份文件",
    group="系统工具",
    order=0,
)
@log_function_call
def system_backups() -> None:
    """查看备份文件。"""
    found_any = False
    for name in BACKUP_SOURCES:
        infos = backup_manager.list_backups(name)
        print(f"\n【{name}】共 {len(infos)} 份备份")
        for info in infos:
            found_any = True
            stamp = info.created_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  - {info.filename}  {info.size / 1024:.1f} KB  {stamp}")
    if not found_any:
        print(f"\n[提示] 暂无备份，备份目录: {backup_manager.backup_dir}")


@registry.register(
    key="system.restore",
    label="恢复备份数据",
    description="从备份文件恢复数据",
    group="系统工具",
    order=1,
)
@log_function_call
def system_restore() -> None:
    """恢复备份数据。"""
    paths = get_path_manager()
    entries: list[tuple[BackupInfo, Path]] = []
    for name in BACKUP_SOURCES:
        target = _backup_target(name)
        entries.extend((info, target) for info in backup_manager.list_backups(name))

    if not entries:
        print("[提示] 未找到任何可恢复的备份")
        return

    print("\n可恢复的备份:")
    for index, (info, target) in enumerate(entries, 1):
        stamp = info.created_at.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {index:>2}. {info.filename}  ->  {paths.relative(target)}  ({stamp})")

    raw = input("\n请选择要恢复的备份序号: ").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= len(entries):
        print("[取消] 无效的序号")
        return

    info, target = entries[int(raw) - 1]
    confirm = input(f"确认用 {info.filename} 覆盖 {paths.relative(target)}? (y/N): ")
    if confirm.strip().lower() != "y":
        print("[取消] 已取消恢复")
        return

    if backup_manager.restore_backup(info.filepath, target):
        print("[完成] 恢复成功")
    else:
        print("[失败] 恢复失败")


@registry.register(
    key="system.config_show",
    label="查看当前配置",
    description="打印关键配置项",
    group="系统工具",
    order=2,
)
@log_function_call
def system_config_show() -> None:
    """查看当前配置。"""
    settings = get_settings()
    paths = get_path_manager()
    print("\n===== 当前配置 =====")
    print("[数据来源]")
    print(f"  米游社用户: {settings.sources.user.url}")
    print(f"  微博:       {settings.sources.weibo.url}")
    print(f"  角色图鉴:   {settings.sources.baike.url}")
    print("[抓取行为]")
    print(f"  headless:     {settings.fetch.headless}")
    print(f"  wait_seconds: {settings.fetch.wait_seconds}")
    print(f"  timeout:      {settings.fetch.timeout} ms")
    print("[新闻站点]")
    for game in settings.sources.news.keys():  # noqa: SIM118 - 保持与配置声明顺序一致
        site = settings.sources.news.get_site(game)
        print(f"  {game:<11} {site.url}")
        print(f"              expected_total = {site.expected_total}")
    print("[存储]")
    print(f"  数据库:   {paths.db}")
    print(f"  配置文件: {paths.config_file}")


@registry.register(
    key="system.config_edit",
    label="修改配置",
    description="交互修改 config.toml 中的常用字段",
    group="系统工具",
    order=3,
)
@log_function_call
def system_config_edit() -> None:
    """修改配置（文本替换，写入前用 tomllib 校验）。"""
    paths = get_path_manager()
    config_path = paths.config_file
    if not config_path.is_file():
        print(f"[错误] 配置文件不存在: {config_path}")
        return

    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[错误] 读取配置失败: {exc}")
        return

    settings = get_settings()
    prompts: tuple[tuple[str, str, str, str, bool], ...] = (
        ("sources.user", "url", "米游社用户 URL", settings.sources.user.url, False),
        ("sources.weibo", "url", "微博 URL", settings.sources.weibo.url, False),
        ("sources.baike", "url", "角色图鉴 URL", settings.sources.baike.url, False),
        ("fetch", "wait_seconds", "页面等待秒数", str(settings.fetch.wait_seconds), True),
    )

    updated = text
    changed: list[str] = []
    for section, key, label, current, is_number in prompts:
        raw = input(f"{label} [当前 {current}] (回车跳过): ").strip()
        if not raw:
            continue
        if is_number:
            try:
                rendered = repr(float(raw))
            except ValueError:
                print(f"[跳过] {label} 输入无效: {raw}")
                continue
        else:
            rendered = f'"{raw}"'

        updated, ok = _set_toml_value(updated, section, key, rendered)
        if ok:
            changed.append(f"{section}.{key}")
        else:
            print(f"[警告] 未在配置文件中定位 {section}.{key}")

    if not changed:
        print("[提示] 未做任何修改")
        return

    try:
        tomllib.loads(updated)
    except tomllib.TOMLDecodeError as exc:
        print(f"[错误] 修改后配置非法，已放弃写入: {exc}")
        return

    config_path.write_text(updated, encoding="utf-8")
    reload_settings()
    print(f"[完成] 已更新: {', '.join(changed)}")
    print(f"配置文件: {config_path}")


@registry.register(
    key="system.config_reload",
    label="重新加载配置",
    description="清除缓存并重新读取 config.toml",
    group="系统工具",
    order=4,
)
@log_function_call
def system_config_reload() -> None:
    """重新加载配置。"""
    settings = reload_settings()
    print("[完成] 配置已重新加载")
    print(f"  headless={settings.fetch.headless}, wait_seconds={settings.fetch.wait_seconds}")


@registry.register(
    key="system.info",
    label="系统信息",
    description="打印运行环境与数据库统计",
    group="系统工具",
    order=5,
)
@log_function_call
def system_info() -> None:
    """系统信息。"""
    paths = get_path_manager()
    print("\n===== 系统信息 =====")
    print(f"  平台:       {platform.platform()}")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  解释器:     {sys.executable}")
    print(f"  工作目录:   {Path.cwd()}")
    print(f"  配置文件:   {paths.config_file}")
    print(f"  工具版本:   {__version__}")
    print(f"  Playwright: {_playwright_version()}")
    print("\n===== SQLite 数据 =====")
    with Storage() as store:
        counts = store.count_all()
        for game, count in counts.items():
            print(f"  news[{game}]: {count}")
        print(f"  news 合计:  {sum(counts.values())}")
        for table in ("posts", "weibo", "tutorial", "images"):
            print(f"  {table}: {store.count_table(table)}")


@registry.register(
    key="system.migrate",
    label="数据迁移工具",
    description="检查并按需迁移旧版 (v1) 数据目录",
    group="系统工具",
    order=6,
)
@log_function_call
def system_migrate() -> None:
    """数据迁移（带交互确认）。"""
    confirm = input("将检查并按需迁移旧版 (v1) 数据，确认继续? (y/N): ")
    if confirm.strip().lower() != "y":
        print("[取消] 已取消数据迁移")
        return
    check_and_migrate()
    print("[完成] 数据迁移检查结束（详情见日志）")


def _collect_cache_targets(root: Path) -> tuple[list[Path], list[Path]]:
    """收集待清理的缓存目录与文件（跳过受保护目录）。"""
    dirs: list[Path] = []
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in PROTECTED_DIRS]
        for name in list(dirnames):
            if name == "__pycache__":
                dirs.append(Path(dirpath) / name)
                dirnames.remove(name)
        files.extend(Path(dirpath) / name for name in filenames if name.endswith((".pyc", ".pyo")))
    for name in BUILD_DIRS:
        candidate = root / name
        if candidate.is_dir():
            dirs.append(candidate)
    return dirs, files


@registry.register(
    key="system.clean",
    label="清理缓存",
    description="删除 __pycache__ / *.pyc / 日志 / 构建产物",
    group="系统工具",
    order=7,
)
@log_function_call
def system_clean() -> None:
    """清理缓存（需输入 YES 确认）。"""
    root = get_path_manager().root
    dirs, files = _collect_cache_targets(root)
    logs_dir = root / "logs"
    logs = sorted(logs_dir.glob("*.log")) if logs_dir.is_dir() else []

    print("\n将清理以下缓存:")
    print(f"  目录: {len(dirs)} 个（__pycache__ / build / dist / .pytest_cache）")
    print(f"  文件: {len(files)} 个（*.pyc / *.pyo）")
    print(f"  日志: {len(logs)} 个（logs/*.log）")
    print(f"  跳过: {', '.join(sorted(PROTECTED_DIRS))}")
    if input("确认清理? 输入 YES 继续: ").strip() != "YES":
        print("[取消] 已取消清理")
        return

    removed_dirs = removed_files = failed = 0
    for path in dirs:
        try:
            shutil.rmtree(path)
            removed_dirs += 1
        except OSError as exc:
            failed += 1
            logger.warning("删除目录失败 %s: %s", path, exc)
    for path in (*files, *logs):
        try:
            path.unlink()
            removed_files += 1
        except OSError as exc:
            failed += 1
            logger.warning("删除文件失败 %s: %s", path, exc)

    print(f"\n[完成] 删除目录 {removed_dirs} 个，文件 {removed_files} 个，失败 {failed} 个")


# ====================================================================== #
#  数据导出
# ====================================================================== #
@registry.register(
    key="export.excel",
    label="导出新闻到 Excel",
    description="将新闻数据导出为 output/news.xlsx",
    group="数据导出",
    order=0,
)
@log_function_call
def export_excel() -> None:
    """导出新闻到 Excel。"""
    path = export_news_excel()
    print(f"[完成] 已导出 Excel: {get_path_manager().relative(path)}")


@registry.register(
    key="export.rss",
    label="导出 RSS Feed",
    description="将新闻数据导出为 RSS 2.0",
    group="数据导出",
    order=1,
)
@log_function_call
def export_rss() -> None:
    """导出 RSS Feed。"""
    path = generate_rss_feed()
    print(f"[完成] 已导出 RSS: {get_path_manager().relative(path)}")


@registry.register(
    key="export.json",
    label="导出 JSON Feed",
    description="将新闻数据导出为 JSON Feed",
    group="数据导出",
    order=2,
)
@log_function_call
def export_json() -> None:
    """导出 JSON Feed。"""
    path = generate_json_feed()
    print(f"[完成] 已导出 JSON: {get_path_manager().relative(path)}")


@registry.register(
    key="export.filter",
    label="TXT 过滤",
    description="按关键词过滤 TXT 数据文件",
    group="数据导出",
    order=3,
)
@log_function_call
def export_filter() -> None:
    """TXT 过滤。"""
    run_filter()


__all__ = ["NEWS_GROUPS"]
