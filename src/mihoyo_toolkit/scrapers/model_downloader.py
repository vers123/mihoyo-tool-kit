"""原神 UP 主激励计划 3D 模型下载器。

移植自 v1 ``fetchers/model_downloader.py``：

* 解析 ``docs/create-plan.md`` 获取各版本 URL 与角色列表；
* 抓取版本活动页面，提取模型下载链接；
* 将下载链接映射到角色名（多种策略，pypinyin 缺失时回退顺序匹配）；
* 下载模型文件到 ``data/models/<version>/<character>/`` 目录。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from tqdm import tqdm

from ..core.config import get_settings
from ..core.paths import get_path_manager
from ..utils.logger import get_module_logger
from .browser import open_browser
from .config import ScrapeConfig

logger = get_module_logger("model_downloader")

_settings = get_settings()
_ATTEMPTS = _settings.retry.max_attempts
_DELAY = _settings.retry.delay
_retry = retry(
    stop=stop_after_attempt(_ATTEMPTS),
    wait=wait_fixed(_DELAY),
    reraise=True,
)


@dataclass
class ModelItem:
    """单个模型下载项。"""

    version: str
    version_name: str
    character: str
    url: str
    filename: str
    matched: bool = True


@dataclass
class VersionInfo:
    """版本信息。"""

    version: str
    version_name: str
    url: str
    characters: list[str]


# ---------------------------------------------------------------------- #
#  create-plan.md 解析
# ---------------------------------------------------------------------- #
def parse_create_plan(plan_path: Path | str | None = None) -> list[VersionInfo]:
    """解析 ``create-plan.md``，提取版本信息列表。"""
    if plan_path is None:
        plan_path = get_path_manager().docs / "create-plan.md"
    plan_path = Path(plan_path)

    if not plan_path.exists():
        logger.error("create-plan.md 不存在: %s", plan_path)
        return []

    content = plan_path.read_text(encoding="utf-8")

    list_section_match = re.search(r"###\s*完整列表.*?```text\s*(.*?)\s*```", content, re.DOTALL)
    if not list_section_match:
        logger.error("create-plan.md 中未找到完整列表代码块")
        return []

    text_content = list_section_match.group(1)
    blocks = re.split(r"\n---\n", text_content)

    versions: list[VersionInfo] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue

        version_match = re.match(r"^(V\d+\.\d+(?:\s+SP)?)\s+(.*)$", lines[0])
        if not version_match:
            continue

        version = version_match.group(1).strip()
        version_name = version_match.group(2).strip()

        current_chars: list[str] | None = None
        i = 1
        while i < len(lines):
            line = lines[i]

            if line.startswith("[*链接"):
                current_chars = None
                i += 1
                continue

            if line.startswith(("http://", "https://")):
                if current_chars is not None:
                    versions.append(
                        VersionInfo(
                            version=version,
                            version_name=version_name,
                            url=line,
                            characters=current_chars,
                        )
                    )
                    current_chars = None
                i += 1
                continue

            char_match = re.match(r"^(?:\d+\s+)?(.+)$", line)
            if char_match:
                chars_str = char_match.group(1).strip()
                if chars_str.startswith("[*序号]") or chars_str == "[*角色名称]":
                    current_chars = None
                else:
                    current_chars = [
                        c.strip() for c in re.split(r"[、,/，]", chars_str) if c.strip()
                    ]
            i += 1

    logger.info("解析到 %d 个版本", len(versions))
    return versions


# ---------------------------------------------------------------------- #
#  下载链接提取
# ---------------------------------------------------------------------- #
def _normalize_url(url: str) -> str:
    """规范化 URL，补全协议、清理脏前缀。"""
    url = url.strip()
    parts = re.split(r"\s+", url)
    for part in reversed(parts):
        if part.startswith(("http://", "https://")):
            url = part
            break
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return "https://" + url
    return url


def _extract_links_from_state(
    obj: Any, results: list[dict[str, str]] | None = None
) -> list[dict[str, str]]:
    """递归从 ``__initialState`` 中提取包含 link 的对象。"""
    if results is None:
        results = []
    if isinstance(obj, dict):
        link = obj.get("link")
        if isinstance(link, str) and link.endswith((".zip", ".rar")):
            results.append(
                {
                    "link": link,
                    "text": obj.get("text", "") or obj.get("title", "") or obj.get("name", ""),
                }
            )
        for value in obj.values():
            _extract_links_from_state(value, results)
    elif isinstance(obj, list):
        for item in obj:
            _extract_links_from_state(item, results)
    return results


def extract_download_links_from_html(html: str, page_url: str = "") -> list[dict[str, Any]]:
    """从 HTML 中提取模型下载链接（多策略）。"""
    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    order = 0

    a_pattern = re.compile(r'<a[^>]*href=["\']([^"\']*?\.(?:rar|zip|7z))["\'][^>]*>', re.IGNORECASE)
    for match in a_pattern.finditer(html):
        url = _normalize_url(match.group(1))
        if url in seen:
            continue
        seen.add(url)
        tag = match.group(0)
        report_match = re.search(r'data-report-click=["\']([^"\']+)["\']', tag)
        links.append(
            {
                "url": url,
                "filename": url.split("/")[-1],
                "report_click": report_match.group(1) if report_match else "",
                "order": order,
            }
        )
        order += 1

    state_pattern = re.compile(r"window\.__initialState\s*=\s*(\{.*?\});", re.DOTALL)
    state_match = state_pattern.search(html)
    if state_match:
        try:
            state = json.loads(state_match.group(1))
            for sl in _extract_links_from_state(state):
                url = _normalize_url(sl["link"])
                if url in seen:
                    continue
                seen.add(url)
                links.append(
                    {
                        "url": url,
                        "filename": url.split("/")[-1],
                        "report_click": sl.get("text", ""),
                        "order": order,
                    }
                )
                order += 1
        except (ValueError, TypeError) as exc:
            logger.debug("解析 __initialState 失败: %s", exc)

    raw_url_pattern = re.compile(r'https?://[^\s"\'<>]+?\.(?:rar|zip|7z)', re.IGNORECASE)
    for match in raw_url_pattern.finditer(html):
        url = _normalize_url(match.group(0))
        if url in seen:
            continue
        seen.add(url)
        links.append(
            {
                "url": url,
                "filename": url.split("/")[-1],
                "report_click": "",
                "order": order,
            }
        )
        order += 1

    return links


# ---------------------------------------------------------------------- #
#  角色名匹配
# ---------------------------------------------------------------------- #
def _get_character_pinyin(character: str) -> str:
    """获取角色名全拼（pypinyin 缺失时返回空串）。"""
    base_name = re.sub(r"[（(].+?[)）]", "", character).strip()
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return ""
    return "".join(lazy_pinyin(base_name))


def _get_character_pinyin_initials(character: str) -> str:
    """获取角色名拼音首字母（pypinyin 缺失时返回空串）。"""
    base_name = re.sub(r"[（(].+?[)）]", "", character).strip()
    try:
        from pypinyin import Style, lazy_pinyin
    except ImportError:
        return ""
    return "".join(lazy_pinyin(base_name, style=Style.FIRST_LETTER))


def _extract_character_from_report_click(report_click: str) -> str:
    """从 ``data-report-click`` 属性提取角色名。"""
    if not report_click:
        return ""
    name = re.sub(r"^caster-[a-z]-", "", report_click)
    name = re.sub(r"模型下载$", "", name)
    name = re.sub(r"^下载-", "", name)
    if re.match(r"^下载模型\d+$", name):
        return ""
    return name.strip()


def _extract_character_from_filename(filename: str) -> str:
    """从文件名 ``【角色名】.zip`` 提取角色名。"""
    match = re.match(r"^【(.+?)】", filename)
    return match.group(1).strip() if match else ""


def _match_char(char_name: str, characters: list[str]) -> str | None:
    """在角色列表中查找与给定名称相关且未使用的角色。"""
    for candidate in characters:
        if char_name in candidate or candidate in char_name:
            return candidate
    return None


def _make_item(character: str, link: dict[str, Any], *, matched: bool = True) -> ModelItem:
    """构造一个未绑定版本信息的 :class:`ModelItem`。"""
    return ModelItem(
        version="",
        version_name="",
        character=character,
        url=link["url"],
        filename=link["filename"],
        matched=matched,
    )


def match_links_to_characters(
    links: list[dict[str, Any]], characters: list[str]
) -> list[ModelItem]:
    """将下载链接映射到角色名（多策略 + 顺序兜底）。"""
    items: list[ModelItem] = []
    used_characters: set[str] = set()

    for link in links:
        matched_char: str | None = None

        # 策略1：data-report-click 匹配
        char_name = _extract_character_from_report_click(link.get("report_click", ""))
        if char_name:
            available = [c for c in characters if c not in used_characters]
            matched_char = _match_char(char_name, available)

        # 策略2：文件名 【角色名】.zip 匹配
        if matched_char is None:
            file_char = _extract_character_from_filename(link["filename"])
            if file_char:
                candidates = []
                for c in characters:
                    base_c = re.sub(r"[（(].+?[)）]", "", c).strip()
                    if file_char == base_c or file_char in c or c in file_char:
                        candidates.append(c)
                matched_char = _match_char(file_char, candidates)

        if matched_char is not None and matched_char not in used_characters:
            items.append(_make_item(matched_char, link))
            used_characters.add(matched_char)
            continue

        # 策略3/4：拼音全拼 / 首字母匹配
        pinyin_full = link["filename"].rsplit(".", 1)[0].lower()
        for c in characters:
            if c in used_characters:
                continue
            char_pinyin = _get_character_pinyin(c).lower()
            if char_pinyin and char_pinyin == pinyin_full:
                matched_char = c
                break
        else:
            for c in characters:
                if c in used_characters:
                    continue
                char_initials = _get_character_pinyin_initials(c).lower()
                if char_initials and char_initials == pinyin_full:
                    matched_char = c
                    break

        if matched_char is not None and matched_char not in used_characters:
            items.append(_make_item(matched_char, link))
            used_characters.add(matched_char)
        else:
            items.append(_make_item("", link, matched=False))

    # 策略5：按顺序匹配剩余链接与角色
    unmatched = [it for it in items if not it.matched]
    remaining = [c for c in characters if c not in used_characters]
    for i, item in enumerate(unmatched):
        if i >= len(remaining):
            break
        item.character = remaining[i]
        item.matched = True
        used_characters.add(remaining[i])

    return items


# ---------------------------------------------------------------------- #
#  抓取与下载
# ---------------------------------------------------------------------- #
def fetch_page_html(url: str) -> str:
    """使用 Playwright 抓取版本活动页面 HTML。"""
    logger.info("抓取页面: %s", url)
    config = ScrapeConfig.from_settings(
        url=url,
        output_filename="_model_page.html",
        scraper_name="model",
        headless=True,
    )
    with open_browser(config) as session:
        session.goto()
        return session.content()


@retry(
    stop=stop_after_attempt(_ATTEMPTS),
    wait=wait_fixed(_DELAY),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
def _stream_to_file(url: str, save_path: Path, timeout: float) -> int:
    """流式下载并返回字节数（HTTP 错误触发重试）。"""
    total = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        with save_path.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=8192):
                fh.write(chunk)
                total += len(chunk)
    return total


def download_file(url: str, save_path: Path, timeout: float = 300.0) -> bool:
    """下载单个模型文件。"""
    if save_path.exists():
        logger.info("文件已存在，跳过: %s", save_path)
        return True

    logger.info("下载: %s", url)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        downloaded = _stream_to_file(url, save_path, timeout)
    except Exception as exc:
        logger.error("下载失败 %s: %s", url, exc)
        save_path.unlink(missing_ok=True)
        return False
    logger.info("下载完成: %s (%d bytes)", save_path, downloaded)
    return True


@_retry
def run_model_download() -> int:
    """执行模型下载主流程，返回成功下载的文件数。"""
    output_dir = get_path_manager().models
    all_versions = parse_create_plan()
    if not all_versions:
        logger.error("没有可下载的版本")
        return 0

    version_items: list[tuple[VersionInfo, list[ModelItem]]] = []
    total_items = 0
    for vi in all_versions:
        try:
            html = fetch_page_html(vi.url)
        except Exception as exc:
            logger.error("抓取版本 %s 页面失败: %s", vi.version, exc)
            continue

        links = extract_download_links_from_html(html, vi.url)
        if not links:
            logger.warning("版本 %s 未找到下载链接", vi.version)
            continue

        items = match_links_to_characters(links, vi.characters)
        for item in items:
            item.version = vi.version
            item.version_name = vi.version_name
        version_items.append((vi, items))
        total_items += len(items)
        logger.info("版本 %s: 找到 %d 个模型", vi.version, len(items))

    success = 0
    failed = 0
    skipped = 0

    pbar = tqdm(total=total_items, desc="模型下载", unit="个") if total_items else None
    try:
        for vi, items in version_items:
            for item in items:
                if pbar is not None:
                    pbar.update(1)

                if not item.matched:
                    logger.warning("未匹配角色，跳过: %s", item.filename)
                    skipped += 1
                    continue

                save_path = output_dir / vi.version / item.character / item.filename
                if save_path.exists():
                    logger.info("已存在，跳过: %s/%s", vi.version, item.character)
                    skipped += 1
                    continue

                if download_file(item.url, save_path):
                    success += 1
                else:
                    failed += 1
    finally:
        if pbar is not None:
            pbar.close()

    logger.info("下载完成: 成功 %d, 失败 %d, 跳过 %d", success, failed, skipped)
    return success


__all__ = [
    "ModelItem",
    "VersionInfo",
    "download_file",
    "extract_download_links_from_html",
    "match_links_to_characters",
    "parse_create_plan",
    "run_model_download",
]
