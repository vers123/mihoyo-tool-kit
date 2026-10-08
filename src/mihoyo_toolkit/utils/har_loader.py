"""HAR 文件解析工具。

从浏览器导出的 HAR 中提取 API 请求模式，作为 API 自动检测失败时的回退。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .. import __version__
from ..core.paths import get_path_manager
from .logger import get_module_logger

logger = get_module_logger("har_loader")

#: 需要 HAR 回退的抓取器清单（启动提示用）
HAR_SITES: list[dict[str, str]] = [
    {
        "name": "米游社用户发帖",
        "scraper_name": "user",
        "url": "https://www.miyoushe.com/ys/accountCenter/postList?id=75276539",
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


def find_har_file(scraper_name: str) -> Path | None:
    """在 ``har/{scraper_name}/`` 下查找第一个 HAR / TXT 文件。"""
    har_dir = get_har_dir(scraper_name)
    if not har_dir.is_dir():
        return None
    for entry in sorted(har_dir.iterdir()):
        if entry.suffix.lower() in {".har", ".txt"}:
            return entry
    return None


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
        lines.append(f"    页面: {site['url']}")
        lines.append(f"    目录: {get_har_dir(site['scraper_name'])}")
    lines += [
        "",
        "  提示：HAR 文件用于自动识别 API 接口，无需手动分析。",
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
        parts.append(
            f"<li><b>{site['name']}</b><br>"
            f'页面: <a href="{site["url"]}">{site["url"]}</a><br>'
            f"目录: <code>{get_har_dir(site['scraper_name'])}</code></li>"
        )
    parts.append(
        "</ul><p>提示：HAR 文件用于自动识别 API 接口，无需手动分析。<br>"
        "如 HAR 已存在且接口正常，可直接使用。</p>"
    )
    return "".join(parts)


__all__ = [
    "HAR_SITES",
    "ensure_har_dirs",
    "extract_api_patterns",
    "find_har_file",
    "get_har_dir",
    "get_har_welcome_html",
    "get_har_welcome_text",
    "load_api_pattern_from_har",
    "load_har_entries",
    "parse_har_file",
    "print_har_instructions",
]
