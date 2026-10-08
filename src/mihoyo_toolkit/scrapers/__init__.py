"""抓取器模块（API 优先 + Playwright 回退）。"""

from __future__ import annotations

from .api_client import MiHoYoApiClient, fetch_all_games, fetch_all_games_async
from .baike import BaikeScraper, run_baike
from .base import BaseScraper
from .browser import BrowserSession, open_browser
from .config import ScrapeConfig
from .custom import CustomScraper, run_custom
from .model_downloader import run_model_download
from .news import (
    GameNewsScraper,
    get_scraper,
    run_all_news,
    run_news,
    run_news_genshin,
    run_news_genshin_en,
    run_news_starrail,
    run_news_zzz,
)
from .tutorial import TutorialScraper, run_tutorial, run_tutorial_batch
from .user import UserScraper, run_user
from .weibo import WeiboScraper, run_weibo

__all__ = [
    # 基础设施
    "BaseScraper",
    "BrowserSession",
    "open_browser",
    "ScrapeConfig",
    "MiHoYoApiClient",
    "fetch_all_games",
    "fetch_all_games_async",
    # 新闻
    "GameNewsScraper",
    "get_scraper",
    "run_news",
    "run_all_news",
    "run_news_genshin",
    "run_news_genshin_en",
    "run_news_zzz",
    "run_news_starrail",
    # 其他来源
    "UserScraper",
    "run_user",
    "WeiboScraper",
    "run_weibo",
    "BaikeScraper",
    "run_baike",
    "TutorialScraper",
    "run_tutorial",
    "run_tutorial_batch",
    "CustomScraper",
    "run_custom",
    "run_model_download",
]
