"""教程数据提取（角色编号 + 更新日志）。

教程数据仍以 HTML 抓取为主，因此保留 v1 的正则解析逻辑：

* :class:`TutorialExtractor` —— 解析角色编号表，结果写入 ``tutorial`` 表
  （:meth:`~mihoyo_toolkit.core.storage.Storage.upsert_tutorial`）并导出 TXT；
* :class:`ChangelogExtractor` —— 解析分层更新日志，导出 JSON（无对应数据表）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..core.exceptions import ParseError
from ..core.models import TutorialItem
from ..core.paths import TUTORIAL_HTML_SUBDIR, get_path_manager
from ..core.storage import Storage
from ..utils.logger import get_module_logger

logger = get_module_logger("extractors.tutorial")

_DEFAULT_TUTORIAL_ID = "mh4imrrhzdzi"
_DEFAULT_CHANGELOG_ID = "mhs2w008wf14"

#: 导出子目录（相对 ``data/results``）
SUBDIR = "tutorial"

# 角色编号表：<tr class="table-row"> 内两列（编号 / 角色名）
_TABLE_PATTERN = re.compile(
    r'<tr class="table-row">.*?'
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?(\d+)(?:</span>)?</p>.*?"
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?([^<]+)(?:</span>)?</p>.*?"
    r"</tr>",
    re.DOTALL,
)
# 宽松兜底：直接匹配两列，编号要求 7 位以上
_LOOSE_PATTERN = re.compile(
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?(\d{7,})(?:</span>)?</p>.*?"
    r"<td[^>]*>.*?<p[^>]*>(?:<span[^>]*>)?([^<]+)(?:</span>)?</p>",
    re.DOTALL,
)


def _html_path(tutorial_id: str, lang: str | None) -> Path:
    """教程 HTML 路径：``data/html/tutorial/tutorial_{id}{_lang}.html``。"""
    suffix = f"_{lang}" if lang else ""
    return get_path_manager().html / TUTORIAL_HTML_SUBDIR / f"tutorial_{tutorial_id}{suffix}.html"


class TutorialExtractor:
    """从教程 HTML 提取角色编号，落库并导出 TXT。"""

    def __init__(
        self,
        tutorial_id: str | None = None,
        lang: str | None = None,
        *,
        db_path: str | Path | None = None,
    ) -> None:
        self.tutorial_id = tutorial_id or _DEFAULT_TUTORIAL_ID
        self.lang = lang
        self._db_path = db_path

    @property
    def html_path(self) -> Path:
        return _html_path(self.tutorial_id, self.lang)

    @property
    def output_path(self) -> Path:
        """导出目标：``data/results/{SUBDIR}/characters_{id}{_lang}.txt``。"""
        suffix = f"_{self.lang}" if self.lang else ""
        return get_path_manager().results / SUBDIR / f"characters_{self.tutorial_id}{suffix}.txt"

    def read_html(self) -> str:
        """读取教程 HTML，缺失时抛 :class:`ParseError`。"""
        if not self.html_path.is_file():
            raise ParseError(f"教程 HTML 不存在: {self.html_path}")
        return self.html_path.read_text(encoding="utf-8")

    def extract_characters(self, html_content: str | None = None) -> list[TutorialItem]:
        """解析角色编号 → 名称列表（按编号升序去重）。"""
        html = html_content if html_content is not None else self.read_html()

        found: dict[str, TutorialItem] = {}
        for match in _TABLE_PATTERN.findall(html):
            char_id = match[0].strip()
            char_name = match[1].strip()
            if char_id == "对应编号" or char_name == "角色名":
                continue
            found.setdefault(
                char_id,
                TutorialItem(character_id=char_id, name=char_name, lang=self.lang or ""),
            )

        if not found:
            logger.warning("[%s] 表格模式未匹配，尝试宽松模式", self.tutorial_id)
            for match in _LOOSE_PATTERN.findall(html):
                char_id = match[0].strip()
                char_name = match[1].strip()
                if len(char_id) >= 7:
                    found.setdefault(
                        char_id,
                        TutorialItem(character_id=char_id, name=char_name, lang=self.lang or ""),
                    )

        items = sorted(found.values(), key=lambda item: int(item.character_id))
        logger.info("[%s] 提取到 %d 个角色", self.tutorial_id, len(items))
        return items

    def store(self, items: list[TutorialItem]) -> int:
        """写入 ``tutorial`` 表，返回新增条数。"""
        with Storage(self._db_path) as store:
            new = store.upsert_tutorial(items)
        logger.info("[%s] 角色入库 %d 条（新增 %d）", self.tutorial_id, len(items), new)
        return new

    def save_character_data(self, items: list[TutorialItem]) -> Path:
        """写出 TXT，返回输出路径。"""
        path_manager = get_path_manager()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"{index:04d}-{item.character_id}-{item.name}" for index, item in enumerate(items, 1)
        ]
        self.output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(
            "[%s] 已导出 %d 个角色 → %s",
            self.tutorial_id,
            len(items),
            path_manager.relative(self.output_path),
        )
        return self.output_path


class ChangelogExtractor:
    """从教程更新日志 HTML 提取版本 / 分类 / 条目 / 链接，导出 JSON。"""

    CHANGELOG_PATTERN = re.compile(r"更新日志|月之[一二三四五六七八九十]+版本|\d+\.0版本")

    def __init__(
        self,
        tutorial_id: str | None = None,
        lang: str | None = None,
    ) -> None:
        self.tutorial_id = tutorial_id or _DEFAULT_CHANGELOG_ID
        self.lang = lang
        self.html_path = _html_path(self.tutorial_id, self.lang)
        suffix = f"_{self.lang}" if self.lang else ""
        self.output_path = (
            get_path_manager().results / SUBDIR / f"changelog_{self.tutorial_id}{suffix}.json"
        )
        self.url = f"https://act.mihoyo.com/ys/ugc/tutorial/detail/{self.tutorial_id}"

    @staticmethod
    def is_changelog(html_content: str) -> bool:
        """检测 HTML 是否为更新日志页面。"""
        return bool(ChangelogExtractor.CHANGELOG_PATTERN.search(html_content or ""))

    def read_html(self) -> str:
        """读取 HTML，缺失时抛 :class:`ParseError`。"""
        if not self.html_path.is_file():
            raise ParseError(f"更新日志 HTML 不存在: {self.html_path}")
        return self.html_path.read_text(encoding="utf-8")

    def extract_all_links(self, html_content: str | None = None) -> list[dict[str, str]]:
        """提取所有教程详情页链接，返回 ``[{title, url, tutorial_id}, ...]``。"""
        html = html_content if html_content is not None else self.read_html()

        a_pattern = re.compile(
            r'<a[^>]*href="([^"]*tutorial[^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        seen_ids: set[str] = set()
        links: list[dict[str, str]] = []
        for match in a_pattern.finditer(html):
            url = match.group(1).strip()
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not url or not title:
                continue
            url = re.sub(r"tutorial//detail", "tutorial/detail", url)
            tid_match = re.search(r"tutorial/detail/([a-z0-9]+)", url)
            if not tid_match:
                continue
            tid = tid_match.group(1)
            if tid in seen_ids or tid == self.tutorial_id:
                continue
            seen_ids.add(tid)
            links.append({"title": title, "url": url, "tutorial_id": tid})
        return links

    def extract(self, html_content: str | None = None) -> dict:
        """解析更新日志为分层字典。"""
        html = html_content if html_content is not None else self.read_html()
        return {
            "page_id": self.tutorial_id,
            "page_title": "更新日志",
            "url": self.url,
            "versions": self._parse_versions(html),
        }

    def _parse_versions(self, html: str) -> list[dict]:
        """解析所有版本段。"""
        version_heading = re.compile(
            r"<h[12][^>]*>\s*([^<]*(?:版本)[^<]*\d{4}/\d{2}/\d{2})\s*</h[12]>",
            re.IGNORECASE,
        )
        matches = list(version_heading.finditer(html))
        if not matches:
            logger.warning("[%s] 未找到版本标题", self.tutorial_id)
            return []

        versions: list[dict] = []
        for index, match in enumerate(matches):
            raw_title = match.group(1).strip()
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(html)
            block = html[start:end]

            version, date = self._split_version_date(raw_title)
            versions.append(
                {
                    "version": version,
                    "date": date,
                    "categories": self._parse_categories(block),
                }
            )
        return versions

    @staticmethod
    def _split_version_date(raw: str) -> tuple[str, str]:
        """将 ``'7.0版本-2026/08/12'`` 拆分为 ``('7.0版本', '2026/08/12')``。"""
        idx = raw.rfind("-")
        if idx > 0 and re.match(r"\d{4}/\d{2}/\d{2}", raw[idx + 1 :]):
            return raw[:idx].strip(), raw[idx + 1 :].strip()
        return raw, ""

    def _parse_categories(self, block: str) -> list[dict]:
        """解析版本块内的分类（内容新增 / 内容修改）。"""
        cat_heading = re.compile(
            r"<h[23][^>]*>\s*([^<]*(?:内容新增|内容修改)[^<]*)\s*</h[23]>",
            re.IGNORECASE,
        )
        matches = list(cat_heading.finditer(block))
        if not matches:
            return []

        categories: list[dict] = []
        for index, match in enumerate(matches):
            raw_title = match.group(1).strip()
            name = re.sub(r"^[一二三四五六七八九十\d]+、", "", raw_title)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
            section = block[start:end]
            categories.append(
                {
                    "name": name,
                    "description": self._extract_description(section),
                    "entries": self._parse_entries(section),
                }
            )
        return categories

    def _parse_entries(self, section: str) -> list[dict]:
        """解析分类区域内的条目（子标题 + 描述 + 链接）。"""
        sub_heading = re.compile(r"<h[34][^>]*>\s*([^<]+)\s*</h[34]>", re.IGNORECASE)
        sub_matches = list(sub_heading.finditer(section))

        entries: list[dict] = []
        if sub_matches:
            for index, smatch in enumerate(sub_matches):
                title = re.sub(r"^\d+\.", "", smatch.group(1).strip()).strip()
                start = smatch.end()
                end = (
                    sub_matches[index + 1].start() if index + 1 < len(sub_matches) else len(section)
                )
                sub_block = section[start:end]
                entries.append(
                    {
                        "title": title,
                        "description": self._extract_description(sub_block),
                        "links": self._extract_links(sub_block),
                    }
                )
        else:
            links = self._extract_links(section)
            if links:
                entries.append(
                    {
                        "title": "",
                        "description": self._extract_description(section),
                        "links": links,
                    }
                )
        return entries

    @staticmethod
    def _extract_description(block: str) -> str:
        """提取 ``<p>`` 标签中的描述文本。"""
        p_pattern = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL)
        texts = []
        for match in p_pattern.finditer(block):
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if text and not text.startswith("更新日志"):
                texts.append(text)
        return "\n".join(texts) if texts else ""

    @staticmethod
    def _extract_links(block: str) -> list[dict[str, str]]:
        """提取 ``<a>`` 标签中的教程链接。"""
        a_pattern = re.compile(
            r'<a[^>]*href="([^"]*tutorial[^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        links: list[dict[str, str]] = []
        for match in a_pattern.finditer(block):
            url = match.group(1).strip()
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if url and title:
                url = re.sub(r"tutorial//detail", "tutorial/detail", url)
                links.append({"title": title, "url": url})
        return links

    def save(self, data: dict) -> Path:
        """写出 JSON，返回输出路径。"""
        path_manager = get_path_manager()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(
            "[%s] 已导出更新日志 → %s", self.tutorial_id, path_manager.relative(self.output_path)
        )
        return self.output_path


def _run_characters(tutorial_id: str, html: str, lang: str | None) -> None:
    extractor = TutorialExtractor(tutorial_id, lang)
    items = extractor.extract_characters(html)
    if not items:
        logger.error("[%s] 未解析到角色数据", tutorial_id)
        return
    extractor.store(items)
    extractor.save_character_data(items)


def _run_changelog(tutorial_id: str, html: str, lang: str | None) -> None:
    extractor = ChangelogExtractor(tutorial_id, lang)
    data = extractor.extract(html)
    if not data.get("versions"):
        logger.error("[%s] 未解析到更新日志数据", tutorial_id)
        return
    extractor.save(data)


def run_extract_tutorial(tutorial_id: str, lang: str | None = None) -> None:
    """解析教程 HTML；自动区分「角色编号」与「更新日志」两类页面。"""
    html_path = _html_path(tutorial_id, lang)
    if not html_path.is_file():
        logger.error("教程 HTML 不存在: %s（请先抓取教程页面）", html_path)
        return

    html = html_path.read_text(encoding="utf-8")
    if ChangelogExtractor.is_changelog(html):
        _run_changelog(tutorial_id, html, lang)
    else:
        _run_characters(tutorial_id, html, lang)


__all__ = ["ChangelogExtractor", "TutorialExtractor", "run_extract_tutorial"]
