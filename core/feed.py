"""新闻 RSS/JSON Feed 生成（D2）

从 SQLite 读取三游戏新闻，生成 RSS 2.0 或 JSON Feed v1.2，供外部订阅。
- RSS：generate_rss_feed() -> output/news_feed.xml
- JSON：generate_json_feed() -> output/news_feed.json
"""

import json
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree as ET

from core.storage import GAME_TABLES, NewsStorage
from utils.logger import get_module_logger

logger = get_module_logger(__name__)

_DEFAULT_RSS = Path("output") / "news_feed.xml"
_DEFAULT_JSON = Path("output") / "news_feed.json"

_GAME_LABELS = {"genshin": "原神", "zzz": "绝区零", "starrail": "星穹铁道"}


def generate_rss_feed(
    games: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Path:
    """生成 RSS 2.0 feed（每条新闻一个 <item>）"""
    if games is None:
        games = list(GAME_TABLES.keys())
    out = Path(output_path) if output_path else _DEFAULT_RSS
    out.parent.mkdir(parents=True, exist_ok=True)

    with NewsStorage(db_path=db_path) as store:
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "米游社新闻"
        ET.SubElement(channel, "link").text = "https://www.miyoushe.com"
        ET.SubElement(channel, "description").text = "原神/绝区零/星穹铁道新闻聚合"
        ET.SubElement(channel, "language").text = "zh-cn"

        total = 0
        for game in games:
            label = _GAME_LABELS.get(game, game)
            for item in store.get_all_items(game):
                el = ET.SubElement(channel, "item")
                ET.SubElement(el, "title").text = f"[{label}] {item['sTitle']}"
                ET.SubElement(el, "link").text = item.get("url", "")
                ET.SubElement(el, "guid", isPermaLink="false").text = (
                    f"{game}-{item['iInfoId']}"
                )
                ET.SubElement(el, "pubDate").text = item.get("date", "")
                ET.SubElement(el, "category").text = label
                desc = item.get("sIntro", "")
                if item.get("poster_url"):
                    desc = f'<img src="{item["poster_url"]}"/>{desc}'
                ET.SubElement(el, "description").text = desc
                total += 1

        ET.indent(rss, space="  ")
        xml_str = ET.tostring(rss, encoding="unicode")
        out.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}',
            encoding="utf-8",
        )

    logger.info(f"RSS feed 已生成: {out}（{total} 条）")
    print(f"\n[OK] RSS feed: {out}（{total} 条）")
    return out


def generate_json_feed(
    games: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Path:
    """生成 JSON Feed v1.2"""
    if games is None:
        games = list(GAME_TABLES.keys())
    out = Path(output_path) if output_path else _DEFAULT_JSON
    out.parent.mkdir(parents=True, exist_ok=True)

    with NewsStorage(db_path=db_path) as store:
        items = []
        for game in games:
            label = _GAME_LABELS.get(game, game)
            for it in store.get_all_items(game):
                items.append(
                    {
                        "id": f"{game}-{it['iInfoId']}",
                        "url": it.get("url", ""),
                        "title": f"[{label}] {it['sTitle']}",
                        "content_html": it.get("sIntro", ""),
                        "date_published": it.get("date", ""),
                        "tags": [label],
                        "image": it.get("poster_url") or None,
                    }
                )
        feed = {
            "version": "https://jsonfeed.org/version/1.2",
            "title": "米游社新闻",
            "home_page_url": "https://www.miyoushe.com",
            "items": items,
        }
        out.write_text(
            json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    logger.info(f"JSON feed 已生成: {out}（{len(items)} 条）")
    print(f"\n[OK] JSON feed: {out}（{len(items)} 条）")
    return out


def run(games: Optional[List[str]] = None, output_path: Optional[str] = None) -> Path:
    """命令行入口：生成 RSS（默认）"""
    return generate_rss_feed(games=games, output_path=output_path)
