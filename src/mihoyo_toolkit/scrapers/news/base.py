"""新闻抓取基类与注册表。

四站点（genshin / genshin_en / zzz / starrail）共用同一 ``content_v2_user``
API 架构，仅配置不同。抓取策略：

1. **API 优先** —— :class:`MiHoYoApiClient` 用 httpx 直连，快速且无浏览器依赖；
2. **Playwright 回退** —— API 返回空时启动浏览器拦截 API 响应；
3. **HAR 回退** —— 浏览器仍无数据时，指引/读取 HAR 文件。
"""

from __future__ import annotations

from typing import Any

from ...core.config import NewsSiteSource, get_settings
from ...core.models import NewsItem
from ...core.paths import get_path_manager
from ...core.storage import Storage
from ...utils.logger import get_module_logger
from ..api_client import MiHoYoApiClient
from ..base import BaseScraper
from ..config import ScrapeConfig

logger = get_module_logger("news")

#: game key → 抓取器类（由子类装饰器注册）
NEWS_SCRAPERS: dict[str, type[GameNewsScraper]] = {}


def register_news(game: str):
    """装饰器：注册新闻抓取器。"""

    def wrapper(cls: type[GameNewsScraper]) -> type[GameNewsScraper]:
        NEWS_SCRAPERS[game] = cls
        return cls

    return wrapper


class GameNewsScraper(BaseScraper[NewsItem]):
    """四站点新闻抓取器基类。"""

    #: 子类覆盖：游戏 key
    game: str = ""

    def __init__(
        self,
        game: str | None = None,
        *,
        incremental: bool | None = None,
        site: NewsSiteSource | None = None,
    ) -> None:
        settings = get_settings()
        key = game or self.game
        if not key:
            raise ValueError("必须指定 game key")
        self.game = key
        self.site = site if site is not None else settings.sources.news.get_site(key)
        self.incremental = settings.incremental.enabled if incremental is None else incremental

        existing: set[str] = set()
        if self.incremental:
            with Storage() as store:
                existing = store.get_existing_urls(self.game)

        config = ScrapeConfig.from_settings(
            url=self.site.url,
            output_filename=self.html_filename,
            scraper_name=self.site.scraper,
            incremental_mode=self.incremental,
            existing_urls=existing,
            api_url_keywords=["getContentList", "content_v2_user"],
            api_domain_filter="mihoyo.com,hoyoverse.com",
            use_firefox_cookies=False,
        )
        super().__init__(config)

    @property
    def name(self) -> str:
        return self.site.scraper

    @property
    def html_filename(self) -> str:
        """HTML 输出文件名，遵循 ``{game}_news.html`` 约定。"""
        return f"{self.game}_news.html"

    # ------------------------------------------------------------------ #
    #  API 拦截解析（Playwright 回退路径）
    # ------------------------------------------------------------------ #
    def extract_items_from_api(self, data: dict[str, Any]) -> list[NewsItem]:
        """复用 :class:`MiHoYoApiClient` 的解析逻辑。"""
        client = MiHoYoApiClient(self.game, site=self.site)
        try:
            return client.extract_items(data)
        except Exception as exc:  # pragma: no cover - 防御性
            logger.debug("解析拦截数据失败: %s", exc)
            return []

    # ------------------------------------------------------------------ #
    #  抓取主入口
    # ------------------------------------------------------------------ #
    def fetch(self) -> list[NewsItem]:
        """抓取新闻：API 优先，失败回退 Playwright，再回退 HAR。"""
        logger.info("[%s] 尝试 API 直连抓取", self.game)
        client = MiHoYoApiClient(
            self.game,
            incremental=self.incremental,
            existing_urls=self.config.existing_urls,
            site=self.site,
        )
        try:
            items = client.fetch_all()
        except Exception as exc:
            logger.warning("[%s] API 直连失败: %s", self.game, exc)
            items = []

        if items:
            logger.info("[%s] API 直连成功，共 %d 条", self.game, len(items))
            return items

        logger.warning("[%s] API 直连无数据，回退 Playwright", self.game)
        self.run()
        if self._api_items:
            return list(self._api_items)

        fallback = self.check_api_or_har()
        if fallback == "use_har":
            logger.info("[%s] 使用 HAR 回退抓取", self.game)
            return self._fetch_from_har()
        return []

    def _fetch_from_har(self) -> list[NewsItem]:
        """从 HAR 文件解析新闻条目。"""
        from ...utils.har_loader import load_har_entries

        scraped: list[NewsItem] = []
        for entry in load_har_entries(self.site.scraper):
            items = self.extract_items_from_api(entry)
            scraped.extend(items)
        logger.info("[%s] HAR 回退解析出 %d 条", self.game, len(scraped))
        return scraped

    # ------------------------------------------------------------------ #
    #  落库
    # ------------------------------------------------------------------ #
    def fetch_and_store(self) -> int:
        """抓取并写入 SQLite，返回新增条数。"""
        items = self.fetch()
        if not items:
            return 0
        with Storage() as store:
            new = store.upsert_news(self.game, items)
        logger.info(
            "[%s] 抓取 %d 条，新增 %d 条（库路径 %s）",
            self.game,
            len(items),
            new,
            get_path_manager().relative(get_path_manager().db),
        )
        return new


def get_scraper(game: str) -> type[GameNewsScraper]:
    """按 game key 获取抓取器类。"""
    if game not in NEWS_SCRAPERS:
        raise KeyError(f"未注册的新闻抓取器: {game}（可用: {sorted(NEWS_SCRAPERS)}）")
    return NEWS_SCRAPERS[game]


def run_news(game: str, *, incremental: bool | None = None) -> int:
    """便捷入口：抓取单个游戏新闻并落库，返回新增条数。"""
    return get_scraper(game)(game, incremental=incremental).fetch_and_store()


def run_all_news(*, incremental: bool | None = None) -> dict[str, int]:
    """抓取全部游戏新闻并落库。"""
    settings = get_settings()
    return {
        game: run_news(game, incremental=incremental)
        for game in settings.sources.news.keys()  # noqa: SIM118 - 自定义方法，非 dict
    }


__all__ = [
    "NEWS_SCRAPERS",
    "GameNewsScraper",
    "get_scraper",
    "register_news",
    "run_all_news",
    "run_news",
]
