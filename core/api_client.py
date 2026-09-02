"""米游社 content_v2_user API 直接客户端

基于 httpx 的同步/异步双接口，绕过浏览器直接请求 content_v2_user API。
作为抓取主路径（O1 去浏览器 + O2 httpx 化），失败时由 fetchers/news/base.py
回退到 Playwright 拦截路径。

- 同步：MiHoYoApiClient(game_key).fetch_all() -> list[dict]
- 异步：await MiHoYoApiClient(game_key).fetch_all_async() -> list[dict]
- 多游戏并发：await fetch_all_games_async(...) -> {game_key: list[dict]}

返回的 item 字段与 fetchers/news/base.py._extract_items_from_api 保持一致，
可直接交给 _build_html_from_api_data 构建页面。
"""

import asyncio
import math
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from core.config_manager import config_manager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)

# 重试配置：网络/HTTP 错误指数退避重试 3 次
_RETRY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=8),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)


class MiHoYoApiClient:
    """米游社 content_v2_user API 客户端

    Args:
        game_key: 游戏标识（genshin / zzz / starrail）
        incremental: 是否增量模式（遇到已存在 URL 停止）
        existing_urls: 增量去重用的已存在 URL 集合
    """

    def __init__(
        self,
        game_key: str,
        incremental: bool = False,
        existing_urls: Optional[set] = None,
    ) -> None:
        self.game_key = game_key
        self.site_config = config_manager.get_news_config(game_key)
        if not self.site_config:
            raise ValueError(f"未找到游戏 '{game_key}' 的新闻配置")
        self.incremental = incremental
        self.existing_urls = existing_urls or set()
        self.user_agent = config_manager.get("user_agent", "")
        self.stop_on_existing = config_manager.get(
            "incremental_settings.stop_on_existing", True
        )
        self.timeout = 30.0
        self._tag = f"[{self.game_key}]"

    # ------------------------------------------------------------------
    # 请求构造与解析
    # ------------------------------------------------------------------
    def _build_page_url(self, page: int) -> str:
        """构造分页请求 URL"""
        params = {
            self.site_config["api_page_param"]: page,
            self.site_config["api_page_size_param"]: self.site_config["api_page_size"],
            "iChanId": self.site_config["api_chan_id"],
            self.site_config.get("api_lang_param", "sLangKey"): self.site_config.get(
                "api_lang_value", "zh-cn"
            ),
        }
        return f"{self.site_config['api_base_url']}?{urlencode(params)}"

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Referer": self.site_config["url"],
        }

    def _extract_items(self, data: dict) -> List[dict]:
        """从 content_v2_user 响应提取新闻列表

        字段格式与 fetchers/news/base.py._extract_items_from_api 一致，
        保证 _build_html_from_api_data 可直接复用。
        """
        import json as _json

        items: List[dict] = []
        if not isinstance(data, dict):
            return items
        list_data = data.get("data", {}).get("list", [])
        if not isinstance(list_data, list):
            return items

        for item in list_data:
            if not isinstance(item, dict):
                continue
            info_id = str(item.get("iInfoId", ""))
            title = item.get("sTitle", "")
            if not info_id or not title:
                continue
            date_str = item.get(self.site_config.get("date_field", "dtStartTime"), "")
            url_path = self.site_config["detail_url_pattern"].format(iInfoId=info_id)
            # O11: 用 Pydantic NewsItem 验证字段后 model_dump 返回 dict，
            # 对外接口不变（storage/excel 仍接收 dict），但增加类型安全
            from core.models import NewsItem

            try:
                news = NewsItem.model_validate(
                    {
                        "iInfoId": info_id,
                        "sTitle": title,
                        "date": str(date_str),
                        "sCategoryName": item.get("sCategoryName", ""),
                        "sIntro": item.get("sIntro", ""),
                        "poster_url": self._extract_poster_url(item),
                        "url": self._make_full_url(url_path),
                    }
                )
                items.append(news.model_dump())
            except Exception:
                # Pydantic 验证失败则跳过该条
                continue
        return items

    def _extract_poster_url(self, item: dict) -> str:
        """从 sExt 中提取封面图 URL"""
        import json as _json

        s_ext_str = item.get("sExt", "")
        if not s_ext_str:
            return ""
        try:
            s_ext = _json.loads(s_ext_str)
        except (ValueError, TypeError):
            return ""
        poster_key = self.site_config.get("poster_ext_key", "")
        if not poster_key or poster_key not in s_ext:
            return ""
        poster_data = s_ext[poster_key]
        if isinstance(poster_data, list) and poster_data:
            return poster_data[0].get("url", "")
        if isinstance(poster_data, dict):
            return poster_data.get("url", "")
        return ""

    def _make_full_url(self, path: str) -> str:
        """将相对路径拼接为完整 URL"""
        if path.startswith("http"):
            return path
        parsed = urlparse(self.site_config["url"])
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    # ------------------------------------------------------------------
    # 同步接口
    # ------------------------------------------------------------------
    def fetch_all(self) -> List[dict]:
        """同步抓取全部新闻（httpx 连接池 + tenacity 重试）

        Returns:
            新闻 item 列表（失败返回空列表，由上层决定是否回退浏览器）
        """
        page_size = self.site_config["api_page_size"]
        all_items: List[dict] = []
        max_pages = 1000
        total = 0
        current_page = 1

        logger.info(
            f"{self._tag} 开始 API 直接抓取（频道 {self.site_config['api_chan_id']}，"
            f"每页 {page_size} 条）"
        )

        try:
            with httpx.Client(
                headers=self._headers(), timeout=self.timeout
            ) as client:
                while current_page <= max_pages:
                    try:
                        data = self._get_page_sync(client, current_page)
                    except httpx.HTTPError as e:
                        logger.warning(
                            f"{self._tag} 第 {current_page} 页请求失败（已重试）: {e}"
                        )
                        break

                    items = self._extract_items(data)
                    if not items:
                        logger.info(f"{self._tag} 第 {current_page} 页无数据，抓取结束")
                        break

                    # 第一页解析总数以收敛 max_pages
                    if current_page == 1:
                        total = data.get("data", {}).get("iTotal", 0)
                        if total:
                            max_pages = min(max_pages, math.ceil(total / page_size))
                            logger.info(
                                f"{self._tag} 新闻总数: {total} 条，共 {max_pages} 页"
                            )

                    all_items.extend(items)
                    logger.info(
                        f"{self._tag} 第 {current_page}/{max_pages} 页: +{len(items)} 条"
                        f"（累计 {len(all_items)} 条）"
                    )

                    # 增量去重：遇到已存在 URL 提前停止
                    if (
                        self.incremental
                        and self.existing_urls
                        and self.stop_on_existing
                        and any(it.get("url", "") in self.existing_urls for it in items)
                    ):
                        logger.info(f"{self._tag} 增量模式：发现已存在数据，停止抓取")
                        break

                    # 不足一页说明是最后一页
                    if len(items) < page_size:
                        logger.info(f"{self._tag} 已到达最后一页")
                        break

                    current_page += 1
        except httpx.HTTPError as e:
            logger.error(f"{self._tag} API 客户端异常: {e}")
            return []

        return all_items

    @retry(**_RETRY)
    def _get_page_sync(self, client: httpx.Client, page: int) -> dict:
        """请求单页（tenacity 重试网络错误）"""
        resp = client.get(self._build_page_url(page))
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # 异步接口（供 asyncio.gather 并发三游戏）
    # ------------------------------------------------------------------
    async def fetch_all_async(self) -> List[dict]:
        """异步抓取全部新闻（httpx.AsyncClient）"""
        page_size = self.site_config["api_page_size"]
        all_items: List[dict] = []
        max_pages = 1000
        total = 0
        current_page = 1

        logger.info(
            f"{self._tag} 开始 API 异步抓取（频道 {self.site_config['api_chan_id']}，"
            f"每页 {page_size} 条）"
        )

        try:
            async with httpx.AsyncClient(
                headers=self._headers(), timeout=self.timeout
            ) as client:
                while current_page <= max_pages:
                    try:
                        data = await self._get_page_async(client, current_page)
                    except httpx.HTTPError as e:
                        logger.warning(
                            f"{self._tag} 第 {current_page} 页请求失败（已重试）: {e}"
                        )
                        break

                    items = self._extract_items(data)
                    if not items:
                        logger.info(f"{self._tag} 第 {current_page} 页无数据，抓取结束")
                        break

                    if current_page == 1:
                        total = data.get("data", {}).get("iTotal", 0)
                        if total:
                            max_pages = min(max_pages, math.ceil(total / page_size))
                            logger.info(
                                f"{self._tag} 新闻总数: {total} 条，共 {max_pages} 页"
                            )

                    all_items.extend(items)
                    logger.info(
                        f"{self._tag} 第 {current_page}/{max_pages} 页: +{len(items)} 条"
                        f"（累计 {len(all_items)} 条）"
                    )

                    if (
                        self.incremental
                        and self.existing_urls
                        and self.stop_on_existing
                        and any(it.get("url", "") in self.existing_urls for it in items)
                    ):
                        logger.info(f"{self._tag} 增量模式：发现已存在数据，停止抓取")
                        break

                    if len(items) < page_size:
                        logger.info(f"{self._tag} 已到达最后一页")
                        break

                    current_page += 1
        except httpx.HTTPError as e:
            logger.error(f"{self._tag} API 异步客户端异常: {e}")
            return []

        return all_items

    @retry(**_RETRY)
    async def _get_page_async(self, client: httpx.AsyncClient, page: int) -> dict:
        """请求单页（异步，tenacity 重试网络错误）"""
        resp = await client.get(self._build_page_url(page))
        resp.raise_for_status()
        return resp.json()


# ----------------------------------------------------------------------
# 多游戏聚合入口
# ----------------------------------------------------------------------
def fetch_all_games(
    game_keys: Optional[List[str]] = None,
    incremental: bool = False,
    existing_urls_map: Optional[Dict[str, set]] = None,
) -> Dict[str, List[dict]]:
    """同步抓取多游戏新闻（顺序执行），返回 {game_key: items}"""
    if game_keys is None:
        game_keys = list(config_manager.get_all_news_sites().keys())
    existing_urls_map = existing_urls_map or {}
    out: Dict[str, List[dict]] = {}
    for gk in game_keys:
        client = MiHoYoApiClient(
            gk,
            incremental=incremental,
            existing_urls=existing_urls_map.get(gk),
        )
        out[gk] = client.fetch_all()
    return out


async def fetch_all_games_async(
    game_keys: Optional[List[str]] = None,
    incremental: bool = False,
    existing_urls_map: Optional[Dict[str, set]] = None,
) -> Dict[str, List[dict]]:
    """并发抓取多游戏新闻（asyncio.gather），返回 {game_key: items}

    供未来调度器/无 GUI 场景使用，三游戏并行可显著缩短总耗时。
    """

    async def _one(gk: str):
        client = MiHoYoApiClient(
            gk,
            incremental=incremental,
            existing_urls=existing_urls_map.get(gk) if existing_urls_map else None,
        )
        return gk, await client.fetch_all_async()

    if game_keys is None:
        game_keys = list(config_manager.get_all_news_sites().keys())
    results = await asyncio.gather(*[_one(gk) for gk in game_keys])
    return dict(results)
