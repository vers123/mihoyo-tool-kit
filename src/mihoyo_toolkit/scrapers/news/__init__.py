"""四站点新闻抓取器。"""

from __future__ import annotations

from .base import (
    NEWS_SCRAPERS,
    GameNewsScraper,
    get_scraper,
    register_news,
    run_all_news,
    run_news,
)
from .genshin import GenshinNewsScraper, run_news_genshin
from .genshin_en import GenshinENNewsScraper, run_news_genshin_en
from .starrail import SRNewsScraper, run_news_starrail
from .zzz import ZZZNewsScraper, run_news_zzz

__all__ = [
    "NEWS_SCRAPERS",
    "GameNewsScraper",
    "GenshinENNewsScraper",
    "GenshinNewsScraper",
    "SRNewsScraper",
    "ZZZNewsScraper",
    "get_scraper",
    "register_news",
    "run_all_news",
    "run_news",
    "run_news_genshin",
    "run_news_genshin_en",
    "run_news_starrail",
    "run_news_zzz",
]
