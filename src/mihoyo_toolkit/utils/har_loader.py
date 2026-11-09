"""HAR 文件解析工具。

从浏览器导出的 HAR 中提取 API 请求模式，作为 API 自动检测失败时的回退。
"""

from __future__ import annotations

import json
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .. import __version__
from ..core.paths import get_path_manager
from .logger import get_module_logger

logger = get_module_logger("har_loader")

#: 自动录制的 HAR 文件前缀
AUTO_HAR_PREFIX = "auto-"

#: HAR 目录中可被加载的文件后缀
HAR_SUFFIXES = frozenset({".har", ".txt"})

#: 自动录制文件名内的时间戳：``auto-YYYYmmdd-HHMMSS``
_AUTO_STAMP_RE = re.compile(r"auto-(\d{8})-(\d{6})")

#: Firefox 导出文件名内的时间戳：``站点_Archive [yy-MM-dd HH-mm-ss]``
_BROWSER_STAMP_RE = re.compile(r"\[(\d{2})-(\d{2})-(\d{2}) (\d{2})-(\d{2})-(\d{2})\]")


def _site_url(site: dict[str, str]) -> str:
    """返回站点的展示 URL；米游社用户页取自配置，避免仓库内硬编码 UID。"""
    if site["scraper_name"] == "user":
        from ..core.config import get_settings

        return get_settings().sources.user.url
    return site["url"]


#: 需要 HAR 回退的抓取器清单（启动提示用）
HAR_SITES: list[dict[str, str]] = [
    {
        "name": "米游社用户发帖",
        "scraper_name": "user",
        # 运行时取自 config.toml / MIHOYO_SOURCES__USER__URL，避免在仓库中硬编码 UID
        "url": "",
    },
    {
        "name": "原神新闻",
        "scraper_name": "news_genshin",
        "url": "https://ys.mihoyo.com/main/news",
    },
    {
        "name": "原神英文版新闻",
        "scraper_name": "news_genshin_en",
        "url": "https://genshin.hoyoverse.com/en/news",
    },
    {
        "name": "绝区零新闻",
        "scraper_name": "news_zzz",
        "url": "https://zzz.mihoyo.com/news",
    },
    {
        "name": "星穹铁道新闻",
        "scraper_name": "news_starrail",
        "url": "https://sr.mihoyo.com/news",
    },
    {
        "name": "微博",
        "scraper_name": "weibo",
        "url": "https://weibo.com/u/6593199887",
    },
    {
        "name": "教程页面（中文）",
        "scraper_name": "tutorial/zh_cn",
        "url": "https://act.mihoyo.com/ys/ugc/tutorial/detail/mhs2w008wf14?lang=zh-cn",
    },
    {
        "name": "教程页面（英文）",
        "scraper_name": "tutorial/en_us",
        "url": "https://act.mihoyo.com/ys/ugc/tutorial/detail/mhs2w008wf14?lang=en-us",
    },
]


def get_har_dir(scraper_name: str) -> Path:
    """返回抓取器对应的 HAR 目录。"""
    return get_path_manager().har_dir(scraper_name)


def ensure_har_dirs() -> None:
    """确保所有抓取器的 HAR 目录存在。"""
    for site in HAR_SITES:
        get_har_dir(site["scraper_name"]).mkdir(parents=True, exist_ok=True)


def list_har_files(scraper_name: str) -> list[Path]:
    """按修改时间倒序列出 HAR 目录下的候选文件（``.har`` / ``.txt``）。"""
    har_dir = get_har_dir(scraper_name)
    if not har_dir.is_dir():
        return []
    files = [
        entry
        for entry in har_dir.iterdir()
        if entry.is_file() and entry.suffix.lower() in HAR_SUFFIXES
    ]
    return sorted(files, key=lambda entry: entry.stat().st_mtime, reverse=True)


def har_saved_at(path: Path) -> datetime:
    """HAR 的保存时间：优先文件名内时间戳，其次文件修改时间。

    只读文件名与元数据（不解析 HAR 内容），因此可以放心用于启动时的批量扫描。
    """
    name = Path(path).name
    match = _AUTO_STAMP_RE.search(name)
    if match:
        with suppress(ValueError):
            return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S")
    match = _BROWSER_STAMP_RE.search(name)
    if match:
        with suppress(ValueError):
            return datetime.strptime("-".join(match.groups()), "%y-%m-%d-%H-%M-%S")
    return datetime.fromtimestamp(Path(path).stat().st_mtime)


def _format_size(size: int) -> str:
    """把字节数渲染为人类可读文本。"""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


@dataclass(frozen=True, slots=True)
class HarFileInfo:
    """HAR 目录中的一个文件。"""

    scraper_name: str
    path: Path
    saved_at: datetime
    size: int
    #: 是否为浏览器回退时自动录制的文件
    auto: bool

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def kind(self) -> str:
        """文件来源（展示用）。"""
        return "自动录制" if self.auto else "手动导出"

    @property
    def saved_at_text(self) -> str:
        return self.saved_at.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def size_text(self) -> str:
        return _format_size(self.size)


@dataclass(frozen=True, slots=True)
class HarSiteStatus:
    """单个抓取器的 HAR 目录状态。"""

    name: str
    scraper_name: str
    directory: Path
    #: 目录内全部 HAR 文件（按保存时间倒序）
    files: list[HarFileInfo]

    @property
    def current(self) -> HarFileInfo | None:
        """当前生效的 HAR（最新文件；加载时仍会优先选含 JSON 响应体的文件）。"""
        return self.files[0] if self.files else None

    @property
    def extra_count(self) -> int:
        """除当前文件外的其他文件数量。"""
        return max(len(self.files) - 1, 0)


@dataclass(frozen=True, slots=True)
class HarCleanupResult:
    """一次 HAR 清理的结果。"""

    removed: list[Path]
    #: 仍保留在磁盘上的文件（含删除失败的文件）
    kept: list[Path]


@dataclass(frozen=True, slots=True)
class HarUpdateReport:
    """一次 HAR 更新（清理 + 状态汇总）的结果。"""

    cleanup: HarCleanupResult
    sites: list[HarSiteStatus]

    @property
    def removed(self) -> list[Path]:
        """本次删除的文件。"""
        return self.cleanup.removed

    @property
    def kept(self) -> list[Path]:
        """本次保留下来的文件。"""
        return self.cleanup.kept


def _har_file_info(path: Path, scraper_name: str = "") -> HarFileInfo:
    return HarFileInfo(
        scraper_name=scraper_name,
        path=path,
        saved_at=har_saved_at(path),
        size=path.stat().st_size,
        auto=path.name.startswith(AUTO_HAR_PREFIX),
    )


def describe_har_files(scraper_name: str) -> list[HarFileInfo]:
    """列出某抓取器 HAR 目录内的文件（按保存时间倒序）。"""
    har_dir = get_har_dir(scraper_name)
    if not har_dir.is_dir():
        return []
    infos = [
        _har_file_info(entry, scraper_name)
        for entry in har_dir.iterdir()
        if entry.is_file() and entry.suffix.lower() in HAR_SUFFIXES
    ]
    return sorted(infos, key=lambda info: info.saved_at, reverse=True)


def har_site_status() -> list[HarSiteStatus]:
    """汇总 :data:`HAR_SITES` 中每个抓取器的 HAR 目录状态。"""
    return [
        HarSiteStatus(
            name=site["name"],
            scraper_name=site["scraper_name"],
            directory=get_har_dir(site["scraper_name"]),
            files=describe_har_files(site["scraper_name"]),
        )
        for site in HAR_SITES
    ]


def _iter_har_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in HAR_SUFFIXES
    ]


def cleanup_har_files(keep: int = 1) -> HarCleanupResult:
    """按保存时间清理 ``har/``：每个目录只保留最新 ``keep`` 个文件。

    额外保护：目录中**最新的手动导出 HAR**（非 ``auto-``）始终保留，避免自动录制的
    空 HAR 遮蔽此前手动导出的有效文件。删除失败（文件被占用）时保留该文件。
    """
    keep = max(1, keep)
    root = get_path_manager().har
    groups: dict[Path, list[Path]] = {}
    for path in _iter_har_files(root):
        groups.setdefault(path.parent, []).append(path)

    removed: list[Path] = []
    kept: list[Path] = []
    for directory in sorted(groups):
        infos = sorted(
            (_har_file_info(path) for path in groups[directory]),
            key=lambda info: info.saved_at,
            reverse=True,
        )
        protected = {info.path for info in infos[:keep]}
        manual = next((info for info in infos if not info.auto), None)
        if manual is not None:
            protected.add(manual.path)

        dir_kept = 0
        for info in infos:
            if info.path in protected:
                kept.append(info.path)
                dir_kept += 1
                continue
            try:
                info.path.unlink()
            except OSError as exc:
                logger.warning("删除旧 HAR 失败 %s: %s", info.path, exc)
                kept.append(info.path)
                dir_kept += 1
            else:
                removed.append(info.path)
        logger.info("HAR 目录 %s：共 %d 个文件，保留 %d 个", directory, len(infos), dir_kept)

    return HarCleanupResult(removed=removed, kept=kept)


def update_har_files(keep: int = 1) -> HarUpdateReport:
    """确保 HAR 目录存在 → 清理旧文件 → 汇总各站点状态。"""
    ensure_har_dirs()
    return HarUpdateReport(cleanup=cleanup_har_files(keep), sites=har_site_status())


def format_har_report(report: HarUpdateReport) -> list[str]:
    """把 HAR 更新结果渲染为 CLI 文本行。"""
    paths = get_path_manager()
    lines = [
        f"[HAR] 已清理旧文件 {len(report.removed)} 个，共保留 {len(report.kept)} 个",
    ]
    for path in report.removed:
        lines.append(f"  - 删除 {paths.relative(path)}")

    lines.append("")
    lines.append("[HAR] 各站点当前生效文件：")
    for status in report.sites:
        current = status.current
        if current is None:
            lines.append(f"  [{status.name}] 缺失 —— 请导出 HAR 放入 {status.directory}")
            continue
        lines.append(
            f"  [{status.name}] {current.name}"
            f"（{current.saved_at_text}，{current.size_text}，{current.kind}）"
        )
        if status.extra_count:
            lines.append(f"      目录内另有 {status.extra_count} 个文件")
    return lines


def _json_payloads(har_path: Path) -> list[dict[str, Any]]:
    """提取 HAR 中所有 JSON 响应体。"""
    payloads: list[dict[str, Any]] = []
    for entry in parse_har_file(har_path):
        content = entry.get("response", {}).get("content", {})
        text = content.get("text")
        if not text:
            continue
        mime = content.get("mimeType", "")
        if "json" not in mime and not text.lstrip().startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _has_json_payload(har_path: Path) -> bool:
    return any(
        (entry.get("response", {}).get("content", {}).get("text") or "").lstrip().startswith("{")
        for entry in parse_har_file(har_path)
    )


def find_har_file(scraper_name: str) -> Path | None:
    """返回最合适的 HAR 文件：优先最新且含 JSON 响应体，其次最新文件。

    自动录制的空 HAR（页面未触发 API）不会遮蔽此前手动导出的有效 HAR。
    """
    files = list_har_files(scraper_name)
    for path in files:
        if _has_json_payload(path):
            return path
    return files[0] if files else None


def auto_har_path(scraper_name: str, now: datetime | None = None) -> Path:
    """生成自动录制 HAR 的目标路径（``har/<scraper>/auto-YYYYmmdd-HHMMSS.har``）。"""
    har_dir = get_har_dir(scraper_name)
    har_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return har_dir / f"{AUTO_HAR_PREFIX}{stamp}.har"


def prune_auto_har_files(scraper_name: str, keep: int) -> None:
    """仅保留最新的 ``keep`` 个自动录制 HAR 文件，手动导出的文件不受影响。"""
    if keep < 1:
        return
    auto_files = [
        path for path in list_har_files(scraper_name) if path.name.startswith(AUTO_HAR_PREFIX)
    ]
    for stale in auto_files[keep:]:
        with suppress(OSError):
            stale.unlink()


def parse_har_file(har_path: Path | str) -> list[dict[str, Any]]:
    """解析 HAR 文件，返回所有 entries（支持多个 JSON 对象拼接）。"""
    content = Path(har_path).read_text(encoding="utf-8", errors="ignore")
    entries: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(content):
        try:
            obj, end_idx = decoder.raw_decode(content, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        if isinstance(obj, dict) and "log" in obj and "entries" in obj["log"]:
            entries.extend(obj["log"]["entries"])
        idx = end_idx
        while idx < len(content) and content[idx] in " \n\r\t":
            idx += 1
    return entries


def load_har_entries(scraper_name: str) -> list[dict[str, Any]]:
    """加载指定抓取器 HAR 中所有 JSON 响应体。

    供新闻抓取器直接复用 :meth:`MiHoYoApiClient.extract_items`。
    """
    har_path = find_har_file(scraper_name)
    if not har_path:
        return []
    return _json_payloads(har_path)


def extract_api_patterns(
    har_path: Path | str, domain_keywords: list[str] | None = None
) -> list[dict[str, Any]]:
    """从 HAR 中提取 GET + JSON 的 API 请求模式。"""
    patterns: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in parse_har_file(har_path):
        req = entry.get("request", {})
        resp = entry.get("response", {})
        url = req.get("url", "")
        if req.get("method", "GET") != "GET":
            continue
        if domain_keywords and not any(kw in url for kw in domain_keywords):
            continue

        content = resp.get("content", {})
        mime = content.get("mimeType", "")
        if "json" not in mime and "text" not in content:
            continue
        if url in seen:
            continue
        seen.add(url)

        patterns.append(
            {
                "url": url,
                "method": "GET",
                "params": {q["name"]: q["value"] for q in req.get("queryString", [])},
                "headers": {h["name"].lower(): h["value"] for h in req.get("headers", [])},
                "has_json_response": "json" in mime,
                "status": resp.get("status", 0),
            }
        )
    return patterns


def load_api_pattern_from_har(
    scraper_name: str, domain_keywords: list[str] | None = None
) -> dict[str, Any] | None:
    """从 HAR 中识别最佳 API 模式。"""
    har_path = find_har_file(scraper_name)
    if not har_path:
        return None

    logger.info("找到 HAR 文件: %s", har_path)
    patterns = extract_api_patterns(har_path, domain_keywords)
    if not patterns:
        logger.warning("HAR 中未找到匹配的 API 请求")
        return None

    json_patterns = [p for p in patterns if p["has_json_response"]] or patterns
    best = json_patterns[0]
    parsed = urlparse(best["url"])
    keep = {
        "ds",
        "x-rpc-app_version",
        "x-rpc-client_type",
        "x-rpc-device_fp",
        "x-rpc-device_id",
        "referer",
        "origin",
    }
    return {
        "url_pattern": parsed.path.split("/")[-1] if parsed.path else "",
        "full_url_template": best["url"],
        "domain": parsed.netloc,
        "params": best["params"],
        "headers": {k: v for k, v in best["headers"].items() if k in keep},
    }


def print_har_instructions(
    scraper_name: str, page_url: str, domain_keywords: list[str] | None = None
) -> None:
    """打印获取 HAR 文件的分步指引。"""
    har_dir = get_har_dir(scraper_name)
    har_dir.mkdir(parents=True, exist_ok=True)
    domains_hint = f"(域名包含: {', '.join(domain_keywords)})" if domain_keywords else ""
    print(
        "\n"
        + "=" * 70
        + "\n[HAR] 自动检测 API 失败，请按以下步骤获取 HAR 文件：\n"
        + "=" * 70
        + f"""
步骤1: 打开 Firefox 浏览器
步骤2: 按 F12 打开开发者工具
步骤3: 切换到「网络」(Network) 面板
步骤4: 勾选「持续日志」(Persist Logs)
步骤5: 访问以下页面并滚动到底部:
       {page_url}
步骤6: 找到返回数据的 JSON 请求 {domains_hint}
步骤7: 右键该请求 → 「保存所有为 HAR」(Save All As HAR)
步骤8: 将 HAR 文件保存到以下目录:
       {har_dir}
步骤9: 保存后重新运行本抓取功能
"""
        + "=" * 70
        + f"\n[INFO] 已创建目录: {har_dir}\n"
        + "[INFO] 请将 HAR 文件放入上述目录后重新运行\n"
        + "=" * 70
        + "\n"
    )


def get_har_welcome_text() -> str:
    """生成 CLI 欢迎语与 HAR 更新步骤（纯文本）。"""
    ensure_har_dirs()
    lines = [
        "=" * 70,
        f"  欢迎使用 米游社工具箱 v{__version__}",
        "=" * 70,
        "",
        "【重要提示】首次使用或接口失效时，请先按以下步骤更新 HAR 文件：",
        "",
        "【首次使用准备】安装 Playwright 浏览器（只需执行一次）：",
        "  pip install playwright",
        "  playwright install chromium",
        "",
        "Firefox 导出 HAR 通用步骤：",
        "  1. 打开 Firefox 浏览器",
        "  2. 按 F12 打开开发者工具",
        "  3. 切换到「网络」(Network) 面板",
        "  4. 勾选「持续日志」(Persist Logs)",
        "  5. 访问目标页面并滚动加载内容",
        "  6. 在网络面板空白处右键 → 「全部内容另存为 HAR」",
        "  7. 将 HAR 文件保存到对应网站的目录中",
        "",
        "各网站 HAR 文件保存目录：",
    ]
    for site in HAR_SITES:
        lines.append(f"  [{site['name']}]")
        lines.append(f"    页面: {_site_url(site)}")
        lines.append(f"    目录: {get_har_dir(site['scraper_name'])}")
    lines += [
        "",
        "  提示：HAR 文件用于自动识别 API 接口，无需手动分析。",
        "  说明：浏览器回退抓取时会自动录制 HAR 到上述目录（[har].auto_update 控制）。",
        "  清理：启动时自动只保留每个目录最新的 HAR（[har].cleanup_on_startup / keep_files 控制）。",
        "  更新：放入新的 HAR 后执行菜单「系统工具 → 更新 HAR 文件」或 mihoyo-toolkit --har。",
        "  如 HAR 已存在且接口正常，可直接使用。",
        "=" * 70,
    ]
    return "\n".join(lines)


def get_har_welcome_html() -> str:
    """生成 GUI 欢迎语与 HAR 更新步骤（HTML）。"""
    ensure_har_dirs()
    parts = [
        f"<h3>欢迎使用 米游社工具箱 v{__version__}</h3>",
        "<p><b>【重要提示】</b>首次使用或接口失效时，请先按以下步骤更新 HAR 文件：</p>",
        "<p><b>【首次使用准备】安装 Playwright 浏览器（只需执行一次）：</b></p>",
        "<pre>pip install playwright\nplaywright install chromium</pre>",
        "<p><b>Firefox 导出 HAR 通用步骤：</b></p>",
        "<ol>",
        "<li>打开 Firefox 浏览器</li>",
        "<li>按 F12 打开开发者工具</li>",
        "<li>切换到「网络」(Network) 面板</li>",
        "<li>勾选「持续日志」(Persist Logs)</li>",
        "<li>访问目标页面并滚动加载内容</li>",
        "<li>在网络面板空白处右键 → 「全部内容另存为 HAR」</li>",
        "<li>将 HAR 文件保存到对应网站的目录中</li>",
        "</ol>",
        "<p><b>各网站 HAR 文件保存目录：</b></p>",
        "<ul>",
    ]
    for site in HAR_SITES:
        url = _site_url(site)
        parts.append(
            f"<li><b>{site['name']}</b><br>"
            f'页面: <a href="{url}">{url}</a><br>'
            f"目录: <code>{get_har_dir(site['scraper_name'])}</code></li>"
        )
    parts.append(
        "</ul><p>提示：HAR 文件用于自动识别 API 接口，无需手动分析。<br>"
        "说明：浏览器回退抓取时会自动录制 HAR 到上述目录（[har].auto_update 控制）。<br>"
        "清理：启动时自动只保留每个目录最新的 HAR"
        "（[har].cleanup_on_startup / keep_files 控制）。<br>"
        "更新：放入新的 HAR 后执行菜单「系统工具 → 更新 HAR 文件」或 "
        "<code>mihoyo-toolkit --har</code>。<br>"
        "如 HAR 已存在且接口正常，可直接使用。</p>"
    )
    return "".join(parts)


__all__ = [
    "AUTO_HAR_PREFIX",
    "HAR_SITES",
    "HAR_SUFFIXES",
    "HarCleanupResult",
    "HarFileInfo",
    "HarSiteStatus",
    "HarUpdateReport",
    "auto_har_path",
    "cleanup_har_files",
    "describe_har_files",
    "ensure_har_dirs",
    "extract_api_patterns",
    "find_har_file",
    "format_har_report",
    "get_har_dir",
    "get_har_welcome_html",
    "get_har_welcome_text",
    "har_saved_at",
    "har_site_status",
    "list_har_files",
    "load_api_pattern_from_har",
    "load_har_entries",
    "parse_har_file",
    "print_har_instructions",
    "prune_auto_har_files",
    "update_har_files",
]
