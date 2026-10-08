"""新闻 Feed 生成（RSS 2.0 / JSON Feed v1.2）。

从 SQLite 读取四站点新闻，供外部订阅：

* :func:`generate_rss_feed` → ``output/news_feed.xml``
* :func:`generate_json_feed` → ``output/news_feed.json``
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from ..core.config import get_settings
from ..core.models import NewsItem
from ..core.paths import get_path_manager
from ..core.storage import Storage
from ..utils.logger import get_module_logger

logger = get_module_logger("exporters.feed")

_FEED_TITLE = "米游社新闻"
_FEED_LINK = "https://www.miyoushe.com"
_FEED_DESCRIPTION = "原神(中/英)/绝区零/星穹铁道新闻聚合"


class FeedGenerator:
    """四站点新闻 → RSS / JSON Feed 生成器。"""

    def __init__(
        self,
        rss_path: str | Path | None = None,
        json_path: str | Path | None = None,
        *,
        db_path: str | Path | None = None,
    ) -> None:
        path_manager = get_path_manager()
        self.rss_path = Path(rss_path) if rss_path else path_manager.output / "news_feed.xml"
        self.json_path = Path(json_path) if json_path else path_manager.output / "news_feed.json"
        self._db_path = db_path

    def _load(self) -> list[tuple[str, str, list[NewsItem]]]:
        """读取各站点新闻，返回 ``[(game, label, items), ...]``。"""
        settings = get_settings()
        groups: list[tuple[str, str, list[NewsItem]]] = []
        with Storage(self._db_path) as store:
            for game in settings.sources.news.keys():  # noqa: SIM118 - 自定义方法，非 dict
                label = settings.sources.news.get_site(game).label
                groups.append((game, label, store.query_news(game)))
        return groups

    def write_rss(self) -> Path:
        """生成 RSS 2.0，返回输出路径。"""
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = _FEED_TITLE
        ET.SubElement(channel, "link").text = _FEED_LINK
        ET.SubElement(channel, "description").text = _FEED_DESCRIPTION
        ET.SubElement(channel, "language").text = "zh-cn"

        total = 0
        for game, label, items in self._load():
            for item in items:
                element = ET.SubElement(channel, "item")
                ET.SubElement(element, "title").text = f"[{label}] {item.sTitle}"
                ET.SubElement(element, "link").text = item.url
                ET.SubElement(element, "guid", isPermaLink="false").text = f"{game}-{item.iInfoId}"
                ET.SubElement(element, "pubDate").text = item.dtStartTime
                ET.SubElement(element, "category").text = label
                description = item.sIntro
                if item.poster_url:
                    description = f'<img src="{item.poster_url}"/>{description}'
                ET.SubElement(element, "description").text = description
                total += 1

        ET.indent(rss, space="  ")
        xml_str = ET.tostring(rss, encoding="unicode")
        self.rss_path.parent.mkdir(parents=True, exist_ok=True)
        self.rss_path.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}', encoding="utf-8"
        )
        logger.info("RSS feed 已生成: %s（%d 条）", self.rss_path, total)
        return self.rss_path

    def write_json(self) -> Path:
        """生成 JSON Feed v1.2，返回输出路径。"""
        items: list[dict[str, object]] = []
        for game, label, news in self._load():
            for item in news:
                items.append(
                    {
                        "id": f"{game}-{item.iInfoId}",
                        "url": item.url,
                        "title": f"[{label}] {item.sTitle}",
                        "content_html": item.sIntro,
                        "date_published": item.dtStartTime,
                        "tags": [label],
                        "image": item.poster_url or None,
                    }
                )

        feed = {
            "version": "https://jsonfeed.org/version/1.2",
            "title": _FEED_TITLE,
            "home_page_url": _FEED_LINK,
            "items": items,
        }
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("JSON feed 已生成: %s（%d 条）", self.json_path, len(items))
        return self.json_path


def generate_rss_feed() -> Path:
    """生成 RSS 2.0 feed 到 ``output/news_feed.xml``。"""
    return FeedGenerator().write_rss()


def generate_json_feed() -> Path:
    """生成 JSON Feed v1.2 到 ``output/news_feed.json``。"""
    return FeedGenerator().write_json()


__all__ = ["FeedGenerator", "generate_json_feed", "generate_rss_feed"]
