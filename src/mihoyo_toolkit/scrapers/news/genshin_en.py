"""原神新闻抓取器（英文）。"""

from __future__ import annotations

from .base import GameNewsScraper, register_news


@register_news("genshin_en")
class GenshinENNewsScraper(GameNewsScraper):
    """原神英文站新闻（genshin.hoyoverse.com，iChanId=395）。"""

    game = "genshin_en"


def run_news_genshin_en(*, incremental: bool | None = None) -> int:
    """抓取原神英文新闻并落库。"""
    return GenshinENNewsScraper("genshin_en", incremental=incremental).fetch_and_store()


__all__ = ["GenshinENNewsScraper", "run_news_genshin_en"]
