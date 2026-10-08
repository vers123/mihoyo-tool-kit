"""米哈游 content_v2_user API 直连客户端（httpx）。

抓取主路径：优先用 httpx 直连 API，速度快且不依赖浏览器。
失败时由 :class:`~mihoyo_toolkit.scrapers.news.base.GameNewsScraper` 回退 Playwright。
"""

from __future__ import annotations

import asyncio
import json
import math
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..core.config import NewsSiteSource, get_settings
from ..core.exceptions import ParseError, RetryExhausted
from ..core.models import NewsItem
from ..utils.logger import get_module_logger

logger = get_module_logger("api_client")


class MiHoYoApiClient:
    """content_v2_user API 客户端。

    Args:
        game: 游戏标识（genshin / genshin_en / zzz / starrail）
        incremental: 增量模式
        existing_urls: 增量去重的已存在 URL 集合
    """

    def __init__(
        self,
        game: str,
        *,
        incremental: bool = False,
        existing_urls: set[str] | None = None,
        site: NewsSiteSource | None = None,
    ) -> None:
        settings = get_settings()
        self.game = game
        self.site = site if site is not None else settings.sources.news.get_site(game)
        self.incremental = incremental
        self.existing_urls = existing_urls or set()
        self.stop_on_existing = settings.incremental.stop_on_existing
        self.user_agent = settings.fetch.user_agent
        self.timeout = 30.0
        self._tag = f"[{self.game}]"

    # ------------------------------------------------------------------ #
    #  请求构造
    # ------------------------------------------------------------------ #
    def build_page_url(self, page: int) -> str:
        """构造分页请求 URL。"""
        params: dict[str, Any] = {
            self.site.api_page_param: page,
            self.site.api_page_size_param: self.site.api_page_size,
            "iChanId": self.site.api_chan_id,
            self.site.api_lang_param: self.site.api_lang_value,
        }
        if self.site.api_app_id:
            params["iAppId"] = self.site.api_app_id
        return f"{self.site.api_base_url}?{urlencode(params)}"

    def headers(self) -> dict[str, str]:
        """请求头。"""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Referer": self.site.url,
        }

    # ------------------------------------------------------------------ #
    #  响应解析
    # ------------------------------------------------------------------ #
    def extract_items(self, data: dict[str, Any]) -> list[NewsItem]:
        """从 content_v2_user 响应提取新闻条目。"""
        if not isinstance(data, dict):
            raise ParseError("API 响应格式非法", detail=type(data).__name__)

        list_data = data.get("data", {}).get("list", [])
        if not isinstance(list_data, list):
            return []

        items: list[NewsItem] = []
        for entry in list_data:
            if not isinstance(entry, dict):
                continue
            info_id = str(entry.get("iInfoId", ""))
            title = entry.get("sTitle", "")
            if not info_id or not title:
                continue
            try:
                items.append(
                    NewsItem(
                        game=self.game,
                        iInfoId=int(info_id),
                        sTitle=str(title),
                        dtStartTime=str(entry.get("dtStartTime", "")),
                        sCategoryName=str(entry.get("sCategoryName", "")),
                        sIntro=str(entry.get("sIntro", "")),
                        poster_url=self._extract_poster_url(entry),
                        url=self._make_full_url(self.site.detail_url(info_id)),
                        raw=entry,
                    )
                )
            except (ValueError, TypeError) as exc:
                logger.debug("%s 跳过非法条目 iInfoId=%s: %s", self._tag, info_id, exc)
                continue
        return items

    def _extract_poster_url(self, entry: dict[str, Any]) -> str:
        """从 sExt 提取封面图 URL。"""
        s_ext_str = entry.get("sExt", "")
        if not s_ext_str:
            return ""
        try:
            s_ext = json.loads(s_ext_str)
        except (ValueError, TypeError):
            return ""
        key = self.site.poster_ext_key
        if not key or not isinstance(s_ext, dict) or key not in s_ext:
            return ""
        poster = s_ext[key]
        if isinstance(poster, list) and poster:
            first = poster[0]
            return first.get("url", "") if isinstance(first, dict) else ""
        if isinstance(poster, dict):
            return poster.get("url", "")
        return ""

    def _make_full_url(self, path: str) -> str:
        """相对路径补全为绝对 URL。"""
        if path.startswith("http"):
            return path
        parsed = urlparse(self.site.url)
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    # ------------------------------------------------------------------ #
    #  抓取
    # ------------------------------------------------------------------ #
    def fetch_all(self) -> list[NewsItem]:
        """同步抓取全部新闻（httpx 连接池 + tenacity 重试）。"""
        page_size = self.site.api_page_size
        max_pages = 1000
        all_items: list[NewsItem] = []
        current_page = 1

        logger.info(
            "%s 开始 API 抓取（频道 %s，每页 %d 条）",
            self._tag,
            self.site.api_chan_id,
            page_size,
        )

        with httpx.Client(headers=self.headers(), timeout=self.timeout) as client:
            while current_page <= max_pages:
                try:
                    data = self._get_page(client, current_page)
                except (httpx.HTTPError, RetryExhausted) as exc:
                    logger.warning(
                        "%s 第 %d 页请求失败（已重试）: %s", self._tag, current_page, exc
                    )
                    if current_page == 1:
                        return []
                    break

                items = self.extract_items(data)
                if not items:
                    logger.info("%s 第 %d 页无数据，抓取结束", self._tag, current_page)
                    break

                if current_page == 1:
                    total = data.get("data", {}).get("iTotal", 0)
                    if total:
                        max_pages = min(max_pages, math.ceil(total / page_size))
                        logger.info("%s 新闻总数: %s 条，共 %d 页", self._tag, total, max_pages)

                all_items.extend(items)
                logger.info(
                    "%s 第 %d/%d 页: +%d 条（累计 %d 条）",
                    self._tag,
                    current_page,
                    max_pages,
                    len(items),
                    len(all_items),
                )

                if self._should_stop(items):
                    logger.info("%s 增量模式：发现已存在数据，停止抓取", self._tag)
                    break
                if len(items) < page_size:
                    logger.info("%s 已到达最后一页", self._tag)
                    break

                current_page += 1

        return all_items

    async def fetch_all_async(self) -> list[NewsItem]:
        """异步抓取全部新闻（httpx.AsyncClient）。"""
        page_size = self.site.api_page_size
        max_pages = 1000
        all_items: list[NewsItem] = []
        current_page = 1

        logger.info("%s 开始 API 异步抓取", self._tag)

        async with httpx.AsyncClient(headers=self.headers(), timeout=self.timeout) as client:
            while current_page <= max_pages:
                try:
                    data = await self._get_page_async(client, current_page)
                except (httpx.HTTPError, RetryExhausted) as exc:
                    logger.warning("%s 第 %d 页异步请求失败: %s", self._tag, current_page, exc)
                    if current_page == 1:
                        return []
                    break

                items = self.extract_items(data)
                if not items:
                    break

                if current_page == 1:
                    total = data.get("data", {}).get("iTotal", 0)
                    if total:
                        max_pages = min(max_pages, math.ceil(total / page_size))

                all_items.extend(items)

                if self._should_stop(items):
                    break
                if len(items) < page_size:
                    break

                current_page += 1

        return all_items

    def _should_stop(self, items: list[NewsItem]) -> bool:
        """增量模式下是否命中已存在数据。"""
        if not (self.incremental and self.existing_urls and self.stop_on_existing):
            return False
        return any(item.url in self.existing_urls for item in items)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _get_page(self, client: httpx.Client, page: int) -> dict[str, Any]:
        resp = client.get(self.build_page_url(page))
        resp.raise_for_status()
        return resp.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def _get_page_async(self, client: httpx.AsyncClient, page: int) -> dict[str, Any]:
        resp = await client.get(self.build_page_url(page))
        resp.raise_for_status()
        return resp.json()


def fetch_all_games(
    games: list[str] | None = None,
    *,
    incremental: bool = False,
    existing_urls_map: dict[str, set[str]] | None = None,
) -> dict[str, list[NewsItem]]:
    """顺序抓取多游戏新闻。"""
    settings = get_settings()
    games = games or settings.sources.news.keys()
    existing_urls_map = existing_urls_map or {}
    return {
        game: MiHoYoApiClient(
            game, incremental=incremental, existing_urls=existing_urls_map.get(game)
        ).fetch_all()
        for game in games
    }


async def fetch_all_games_async(
    games: list[str] | None = None,
    *,
    incremental: bool = False,
    existing_urls_map: dict[str, set[str]] | None = None,
) -> dict[str, list[NewsItem]]:
    """并发抓取多游戏新闻（asyncio.gather）。"""
    settings = get_settings()
    games = games or settings.sources.news.keys()
    existing_urls_map = existing_urls_map or {}

    async def _one(game: str) -> tuple[str, list[NewsItem]]:
        client = MiHoYoApiClient(
            game, incremental=incremental, existing_urls=existing_urls_map.get(game)
        )
        return game, await client.fetch_all_async()

    results = await asyncio.gather(*[_one(g) for g in games])
    return dict(results)


__all__ = ["MiHoYoApiClient", "fetch_all_games", "fetch_all_games_async"]
