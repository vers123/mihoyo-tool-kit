"""原神新闻抓取器（中文）。"""

from __future__ import annotations

from .base import GameNewsScraper, register_news


@register_news("genshin")
class GenshinNewsScraper(GameNewsScraper):
    """原神官网新闻（ys.mihoyo.com，iChanId=719）。"""

    game = "genshin"


def run_news_genshin(*, incremental: bool | None = None) -> int:
    """抓取原神新闻并落库。"""
    return GenshinNewsScraper("genshin", incremental=incremental).fetch_and_store()


__all__ = ["GenshinNewsScraper", "run_news_genshin"]
