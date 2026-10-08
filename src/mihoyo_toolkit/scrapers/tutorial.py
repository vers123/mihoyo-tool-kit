"""米游社教程页面抓取器。

移植自 v1 ``fetchers/tutorial.py`` + ``extractors/tutorial.py``：

* 抓取教程详情页（HTML 保存为 ``data/html/tutorial/tutorial_{id}_{lang}.html``，强制后台运行）；
* 从教程表格解析角色编号 / 名称，落库到 ``tutorial`` 表（不再写 TXT）；
* 批量模式从更新日志/目录页提取所有教程链接并逐个抓取。
"""

from __future__ import annotations

import re
from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

from ..core.config import get_settings
from ..core.models import TutorialItem
from ..core.paths import TUTORIAL_HTML_SUBDIR
from ..core.storage import Storage
from ..utils.logger import get_module_logger
from .base import BaseScraper
from .config import ScrapeConfig

logger = get_module_logger("tutorial")

_settings = get_settings()
_retry = retry(
    stop=stop_after_attempt(_settings.retry.max_attempts),
    wait=wait_fixed(_settings.retry.delay),
    reraise=True,
)

DEFAULT_TUTORIAL_ID = "mh4imrrhzdzi"
DEFAULT_INDEX_ID = "mhs2w008wf14"

_URL_PREFIX = "https://act.mihoyo.com/ys/ugc/tutorial/detail"

_TABLE_PATTERN = re.compile(
    r'<tr class="table-row">.*?'
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?(\d+)(?:</span>)?</p>.*?"
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?([^<]+)(?:</span>)?</p>.*?"
    r"</tr>",
    re.DOTALL,
)

_LOOSE_TABLE_PATTERN = re.compile(
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?(\d{7,})(?:</span>)?</p>.*?"
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?([^<]+)(?:</span>)?</p>",
    re.DOTALL,
)

_CHANGELOG_PATTERN = re.compile(r"更新日志|月之[一二三四五六七八九十]+版本|\d+\.0版本")

_LINK_PATTERN = re.compile(
    r'<a[^>]*href="([^"]*tutorial[^"]*)"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)


def _lang_suffix(lang: str | None) -> str:
    return lang or "default"


def _extract_characters(html: str) -> list[tuple[str, str]]:
    """从教程 HTML 表格解析 (角色编号, 角色名) 列表。"""
    characters: list[tuple[str, str]] = []

    for char_id, char_name in _TABLE_PATTERN.findall(html):
        char_id = char_id.strip()
        char_name = char_name.strip()
        if char_id != "对应编号" and char_name != "角色名":
            characters.append((char_id, char_name))

    if not characters:
        logger.info("主表格模式未匹配，尝试宽松模式")
        for char_id, char_name in _LOOSE_TABLE_PATTERN.findall(html):
            char_id = char_id.strip()
            if len(char_id) >= 7:
                characters.append((char_id, char_name.strip()))

    # 去重并按编号升序
    unique = sorted(set(characters), key=lambda item: int(item[0]))
    return unique


def _is_changelog(html: str) -> bool:
    """检测 HTML 是否为更新日志 / 目录页。"""
    return bool(_CHANGELOG_PATTERN.search(html or ""))


def _extract_all_links(html: str, index_id: str) -> list[dict[str, str]]:
    """从目录页提取所有教程详情链接。"""
    seen_ids: set[str] = set()
    links: list[dict[str, str]] = []
    for match in _LINK_PATTERN.finditer(html):
        url = match.group(1).strip()
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if not url or not title:
            continue
        url = re.sub(r"tutorial//detail", "tutorial/detail", url)
        tid_match = re.search(r"tutorial/detail/([a-z0-9]+)", url)
        if not tid_match:
            continue
        tid = tid_match.group(1)
        if tid in seen_ids or tid == index_id:
            continue
        seen_ids.add(tid)
        links.append({"title": title, "url": url, "tutorial_id": tid})
    return links


class TutorialScraper(BaseScraper[TutorialItem]):
    """教程详情页抓取器（强制后台运行）。"""

    def __init__(self, tutorial_id: str, lang: str | None = None) -> None:
        url = f"{_URL_PREFIX}/{tutorial_id}"
        if lang:
            url += f"?lang={lang}"

        config = ScrapeConfig.from_settings(
            url=url,
            output_filename=f"tutorial_{tutorial_id}_{_lang_suffix(lang)}.html",
            html_subdir=TUTORIAL_HTML_SUBDIR,
            scraper_name="tutorial",
            headless=True,  # 教程抓取强制后台运行
        )
        super().__init__(config)
        self.tutorial_id = tutorial_id
        self.lang = lang

    @property
    def name(self) -> str:
        return f"tutorial/{_lang_suffix(self.lang)}"

    def extract_items_from_api(self, data: dict[str, Any]) -> list[TutorialItem]:
        """教程页面不使用 API 拦截。"""
        return []

    def parse(self, html: str) -> list[TutorialItem]:
        """从 HTML 解析教程角色数据。"""
        lang = self.lang or ""
        return [
            TutorialItem(character_id=char_id, name=name, lang=lang)
            for char_id, name in _extract_characters(html)
        ]


@_retry
def run_tutorial(tutorial_id: str, lang: str | None = None) -> None:
    """抓取单个教程详情页并落库角色数据。"""
    if not tutorial_id:
        tutorial_id = DEFAULT_TUTORIAL_ID
    logger.info("抓取教程页面: %s (lang=%s)", tutorial_id, lang or "默认")

    scraper = TutorialScraper(tutorial_id, lang)
    html = scraper.run()
    items = scraper.parse(html)
    if not items:
        logger.warning("教程 %s 未解析到角色数据", tutorial_id)
        return

    with Storage() as store:
        new = store.upsert_tutorial(items)
    logger.info("教程 %s 解析 %d 个角色，新增 %d 条", tutorial_id, len(items), new)


def run_tutorial_batch(index_id: str, lang: str | None = None) -> int:
    """抓取目录索引页，提取所有教程链接并逐个抓取，返回成功抓取数。"""
    if not index_id:
        index_id = DEFAULT_INDEX_ID
    logger.info("批量抓取教程页面，索引ID: %s (lang=%s)", index_id, lang or "默认")
    logger.info("索引页: %s/%s", _URL_PREFIX, index_id)

    scraper = TutorialScraper(index_id, lang)
    html = scraper.run()
    if not _is_changelog(html):
        logger.warning("该页面不是更新日志/目录页，无法提取链接")
        return 0

    links = _extract_all_links(html, index_id)
    if not links:
        logger.error("未提取到任何教程链接")
        return 0
    logger.info("共发现 %d 个教程页面", len(links))

    suffix = _lang_suffix(lang)
    html_dir = scraper.html_path.parent  # data/html/tutorial
    total = len(links)
    success = 0

    for i, link in enumerate(links, 1):
        tid = link["tutorial_id"]
        title = link["title"]
        target = html_dir / f"tutorial_{tid}_{suffix}.html"
        if target.exists():
            logger.info("[%d/%d] 跳过（已存在）: %s (%s)", i, total, title, tid)
            continue
        logger.info("[%d/%d] 抓取: %s (%s)", i, total, title, tid)
        try:
            run_tutorial(tid, lang)
            success += 1
        except Exception as exc:
            logger.error("抓取失败 %s: %s", tid, exc)

    logger.info("批量抓取完成: 成功 %d / 共 %d", success, total)
    return success


__all__ = ["TutorialScraper", "run_tutorial", "run_tutorial_batch"]
