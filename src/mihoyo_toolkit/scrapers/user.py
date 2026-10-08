"""米游社用户发帖抓取器。

移植自 v1 ``fetchers/user.py``，改用 v2 基础设施：

* ``BrowserSession`` 管理浏览器与 Firefox Cookie 注入；
* ``BaseScraper`` 提供 API 响应拦截 / 滚动 / 增量提前终止 / HAR 回退；
* 抓取结果落库到 ``posts`` 表（不再写 TXT）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm

from ..core.config import get_settings
from ..core.models import PostItem
from ..core.storage import Storage
from ..utils.har_loader import load_har_entries
from ..utils.logger import get_module_logger
from .base import BaseScraper
from .config import ScrapeConfig

logger = get_module_logger("user")

_settings = get_settings()
_retry = retry(
    stop=stop_after_attempt(_settings.retry.max_attempts),
    wait=wait_fixed(_settings.retry.delay),
    reraise=True,
)


def _load_existing_post_urls() -> set[str]:
    """从 ``posts`` 表读取已存在的帖子 URL（增量终止判断用）。

    ``Storage`` 门面当前仅暴露新闻表的 :meth:`get_existing_urls`，
    故这里复用其公开连接读取 posts 表。
    """
    with Storage() as store:
        rows = store.connect().execute("SELECT url FROM posts WHERE url <> ''").fetchall()
    return {str(row["url"]) for row in rows}


class UserScraper(BaseScraper[PostItem]):
    """米游社用户发帖抓取器（API 拦截 + HAR 回退）。"""

    def __init__(self, incremental: bool = False) -> None:
        settings = get_settings()
        existing: set[str] = set()
        if incremental:
            existing = _load_existing_post_urls()
            logger.info("增量模式: 已存在 %d 条用户发帖", len(existing))

        config = ScrapeConfig.from_settings(
            url=settings.sources.user.url,
            output_filename="user_posts.html",
            scraper_name="user",
            incremental_mode=incremental,
            existing_urls=existing,
            api_url_keywords=["userPostList", "postList"],
            api_domain_filter="miyoushe.com",
            use_firefox_cookies=settings.cookies.use_firefox,
        )
        super().__init__(config)
        self.url_selector_template = "a[href*='/ys/article/']"

    @property
    def name(self) -> str:
        return "user"

    # ------------------------------------------------------------------ #
    #  API 解析
    # ------------------------------------------------------------------ #
    def extract_items_from_api(self, data: dict[str, Any]) -> list[PostItem]:
        """从 ``postList`` API 响应提取帖子列表。"""
        if not isinstance(data, dict):
            return []
        post_list = data.get("data", {}).get("list", [])
        if not isinstance(post_list, list):
            return []

        items: list[PostItem] = []
        for post_item in post_list:
            if not isinstance(post_item, dict):
                continue
            post = post_item.get("post", post_item)
            if not isinstance(post, dict):
                continue
            post_id = post.get("post_id", "")
            if not post_id:
                continue

            created_at = post.get("created_at", 0)
            if isinstance(created_at, (int, float)) and created_at > 0:
                date_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d")
            else:
                date_str = str(created_at)

            items.append(
                PostItem(
                    post_id=str(post_id),
                    title=str(post.get("subject", "")),
                    created_at=date_str,
                    url=f"https://www.miyoushe.com/ys/article/{post_id}",
                    content=str(post.get("content", "")),
                )
            )
        return items

    # ------------------------------------------------------------------ #
    #  抓取主入口
    # ------------------------------------------------------------------ #
    def fetch(self) -> list[PostItem]:
        """抓取：API 拦截优先，失败回退 HAR。"""
        pbar = tqdm(desc="用户发帖抓取", unit="次")

        def _tick(_: int) -> None:
            pbar.update(1)
            pbar.set_postfix(条数=len(self._api_items))

        try:
            self.run(on_progress=_tick)
        finally:
            pbar.close()

        if self._api_items:
            return list(self._api_items)

        if self.check_api_or_har() == "use_har":
            return self._fetch_from_har()
        return []

    def _fetch_from_har(self) -> list[PostItem]:
        """从 HAR 文件回退解析帖子。"""
        items: list[PostItem] = []
        for payload in load_har_entries(self.config.scraper_name):
            items.extend(self.extract_items_from_api(payload))
        logger.info("HAR 回退解析出 %d 条发帖", len(items))
        return items

    def fetch_and_store(self) -> int:
        """抓取并写入 SQLite，返回新增条数。"""
        items = self.fetch()
        if not items:
            logger.warning("未获取到任何用户发帖")
            return 0
        with Storage() as store:
            new = store.upsert_posts(items)
        logger.info("用户发帖抓取 %d 条，新增 %d 条", len(items), new)
        return new


@_retry
def run_user(incremental: bool = False) -> int:
    """抓取用户发帖主页并落库，返回新增条数。"""
    mode = "增量" if incremental else "全量"
    logger.info("开始%s抓取用户发帖主页", mode)
    return UserScraper(incremental=incremental).fetch_and_store()


__all__ = ["UserScraper", "run_user"]
