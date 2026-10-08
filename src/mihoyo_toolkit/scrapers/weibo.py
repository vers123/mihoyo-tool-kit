"""微博用户主页抓取器。

移植自 v1 ``fetchers/weibo.py``，改用 v2 基础设施：

* 优先通过微博 AJAX 接口（``statuses/mymblog``，``since_id`` 游标分页）抓取全部微博；
* Firefox Cookie 注入实现免登录，Cookie 失效时切换可见浏览器供手动登录；
* 失败回退 HAR；结果落库到 ``weibo`` 表（不再写 TXT）。
"""

from __future__ import annotations

import re
import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm

from ..core.config import get_settings
from ..core.models import WeiboItem
from ..core.storage import Storage
from ..utils.har_loader import load_har_entries
from ..utils.logger import get_module_logger
from .base import BaseScraper
from .browser import BrowserSession
from .config import ScrapeConfig

logger = get_module_logger("weibo")

_settings = get_settings()
_retry = retry(
    stop=stop_after_attempt(_settings.retry.max_attempts),
    wait=wait_fixed(_settings.retry.delay),
    reraise=True,
)

_DEFAULT_UID = "6593199887"
_TAG_RE = re.compile(r"<[^>]+>")


def _load_existing_weibo_urls() -> set[str]:
    """从 ``weibo`` 表读取已存在的微博 URL（增量终止判断用）。"""
    with Storage() as store:
        rows = store.connect().execute("SELECT url FROM weibo WHERE url <> ''").fetchall()
    return {str(row["url"]) for row in rows}


class WeiboScraper(BaseScraper[WeiboItem]):
    """微博用户主页抓取器（AJAX API + HAR 回退）。"""

    def __init__(self, incremental: bool = False) -> None:
        settings = get_settings()
        existing: set[str] = set()
        if incremental:
            existing = _load_existing_weibo_urls()
            logger.info("增量模式: 已存在 %d 条微博", len(existing))

        weibo_url = settings.sources.weibo.url
        self.user_id = self._extract_user_id(weibo_url)

        config = ScrapeConfig.from_settings(
            url=weibo_url,
            output_filename="weibo_posts.html",
            scraper_name="weibo",
            incremental_mode=incremental,
            existing_urls=existing,
            api_url_keywords=["mymblog", "statuses"],
            api_domain_filter="weibo.com",
            use_firefox_cookies=settings.cookies.use_firefox,
        )
        super().__init__(config)
        self.url_selector_template = f"a[href*='/{self.user_id}/']"

    @property
    def name(self) -> str:
        return "weibo"

    # ------------------------------------------------------------------ #
    #  API 解析
    # ------------------------------------------------------------------ #
    def extract_items_from_api(self, data: dict[str, Any]) -> list[WeiboItem]:
        """从 ``statuses/mymblog`` 响应提取微博条目。"""
        if not isinstance(data, dict):
            return []
        data_obj = data.get("data", {})
        if not isinstance(data_obj, dict):
            return []
        post_list = data_obj.get("list", [])
        if not isinstance(post_list, list):
            return []

        items: list[WeiboItem] = []
        for post in post_list:
            if not isinstance(post, dict):
                continue
            item = self._parse_post(post)
            if item is not None:
                items.append(item)
        return items

    def _parse_post(self, post: dict[str, Any]) -> WeiboItem | None:
        """解析单条微博（兼容 mblogid / bid / mid / idstr 字段）。"""
        post_id = (
            post.get("mblogid") or post.get("bid") or post.get("mid") or post.get("idstr") or ""
        )
        if not post_id:
            return None

        raw_text = post.get("text_raw") or post.get("text") or ""
        text = _TAG_RE.sub("", str(raw_text)).strip()

        return WeiboItem(
            post_id=str(post_id),
            text=text,
            created_at=str(post.get("created_at", "")),
            url=f"https://weibo.com/{self.user_id}/{post_id}",
            reposts=int(post.get("reposts_count", 0) or 0),
            comments=int(post.get("comments_count", 0) or 0),
            attitudes=int(post.get("attitudes_count", 0) or 0),
        )

    @staticmethod
    def _extract_user_id(url: str) -> str:
        match = re.search(r"/u/(\d+)", url)
        return match.group(1) if match else _DEFAULT_UID

    # ------------------------------------------------------------------ #
    #  登录检测
    # ------------------------------------------------------------------ #
    @staticmethod
    def _needs_login(page: Any) -> bool:
        try:
            return page.locator(".wbpro-scroller-item").count() == 0
        except Exception:
            return True

    def _wait_for_login(self, page: Any) -> None:
        """Cookie 失效时提示用户手动登录（保留 print 供用户可见）。"""
        if not self._needs_login(page):
            return
        print("\n" + "=" * 60)
        print("[INFO] Cookie 未生效，需要手动登录微博")
        print("[INFO] 请在弹出的浏览器窗口中完成登录...")
        print("[INFO] 登录成功后程序将自动继续抓取")
        print("=" * 60)

        max_attempts = 300  # 最多等待约 10 分钟
        for _ in range(max_attempts):
            if not self._needs_login(page):
                logger.info("登录成功，继续抓取")
                return
            time.sleep(2)
        logger.warning("等待登录超时，尝试继续抓取")

    def _get_xsrf_token(self, page: Any) -> str:
        """从 Cookie 中提取微博 API 必需的 XSRF-TOKEN。"""
        try:
            for cookie in page.context.cookies():
                if cookie.get("name") == "XSRF-TOKEN":
                    return str(cookie.get("value", ""))
        except Exception as exc:
            logger.warning("获取 XSRF-TOKEN 失败: %s", exc)
        return ""

    # ------------------------------------------------------------------ #
    #  AJAX 分页抓取
    # ------------------------------------------------------------------ #
    def _fetch_posts_via_api(self, session: BrowserSession) -> list[WeiboItem]:
        """通过微博 AJAX API 分页获取全部微博数据。"""
        page = session.page
        uid = self.user_id
        scroll_delay = self.config.scroll_delay
        incremental_enabled = bool(self.config.incremental_mode and self.config.existing_urls)
        stop_on_existing = get_settings().incremental.stop_on_existing

        all_posts: dict[str, WeiboItem] = {}
        current_page = 1
        since_id = ""
        pbar: Any = None

        xsrf_token = self._get_xsrf_token(page)
        if xsrf_token:
            logger.info("已获取 XSRF-TOKEN")
        else:
            logger.warning("未找到 XSRF-TOKEN，API 可能返回空数据")

        referer_url = f"https://weibo.com/u/{uid}"
        request_context = page.request

        while True:
            api_url = (
                f"https://weibo.com/ajax/statuses/mymblog?uid={uid}&page={current_page}&feature=0"
            )
            if since_id:
                api_url += f"&since_id={since_id}"

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Referer": referer_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            if xsrf_token:
                headers["X-XSRF-TOKEN"] = xsrf_token

            try:
                response = request_context.get(api_url, headers=headers)
            except Exception as exc:
                logger.error("API 请求异常 (page=%d): %s", current_page, exc)
                break

            if not response.ok:
                logger.warning("API 请求失败 (page=%d): HTTP %s", current_page, response.status)
                if current_page == 1:
                    logger.error("第一页请求失败，请确认已登录微博")
                break

            result = response.json()
            data = result.get("data", {}) if isinstance(result, dict) else {}
            if not isinstance(data, dict):
                data = {}

            items = self.extract_items_from_api(result)
            total = int(data.get("total", 0) or 0)
            if pbar is None and total > 0:
                pbar = tqdm(total=total, desc="微博抓取", unit="条")

            if not items:
                logger.info("第 %d 页无数据，抓取完成", current_page)
                break

            for item in items:
                all_posts.setdefault(item.url, item)
            if pbar is not None:
                pbar.update(len(items))

            if (
                incremental_enabled
                and stop_on_existing
                and any(item.url in self.config.existing_urls for item in items)
            ):
                logger.info("发现已存在数据，增量模式停止 (已收集 %d 条)", len(all_posts))
                break

            # 防护：已翻多页仍无解析结果，说明字段可能变化
            if current_page >= 3 and not all_posts:
                logger.warning(
                    "第 %d 页仍未解析到帖子，可能 API 字段已变化，终止抓取", current_page
                )
                break

            new_since_id = str(data.get("since_id", "") or "")
            if not new_since_id or new_since_id == since_id:
                logger.info("since_id 已耗尽，抓取完成 (共 %d 条)", len(all_posts))
                break

            since_id = new_since_id
            current_page += 1
            time.sleep(scroll_delay)

        if pbar is not None:
            pbar.close()
        logger.info("API 抓取完成，共收集 %d 条微博", len(all_posts))
        return list(all_posts.values())

    # ------------------------------------------------------------------ #
    #  抓取主入口
    # ------------------------------------------------------------------ #
    def fetch(self) -> list[WeiboItem]:
        """抓取微博：AJAX API 优先，失败回退 HAR。"""
        session = BrowserSession(self.config).start()
        try:
            session.goto()
            if self._needs_login(session.page) and self.config.headless:
                logger.info("Cookie 未生效，切换到可见浏览器窗口供手动登录")
                session.stop()
                self.config.headless = False
                session = BrowserSession(self.config).start()
                session.goto()

            self._wait_for_login(session.page)
            self.save_html(session.content())
            items = self._fetch_posts_via_api(session)
        finally:
            session.stop()

        if items:
            return items

        if self.check_api_or_har() == "use_har":
            return self._fetch_from_har()
        return []

    def _fetch_from_har(self) -> list[WeiboItem]:
        """从 HAR 文件回退解析微博。"""
        items: list[WeiboItem] = []
        for payload in load_har_entries(self.config.scraper_name):
            items.extend(self.extract_items_from_api(payload))
        logger.info("HAR 回退解析出 %d 条微博", len(items))
        return items

    def fetch_and_store(self) -> int:
        """抓取并写入 SQLite，返回新增条数。"""
        items = self.fetch()
        if not items:
            logger.warning("未获取到任何微博数据")
            return 0
        with Storage() as store:
            new = store.upsert_weibo(items)
        logger.info("微博抓取 %d 条，新增 %d 条", len(items), new)
        return new


@_retry
def run_weibo(incremental: bool = False) -> int:
    """抓取微博用户主页并落库，返回新增条数。"""
    mode = "增量" if incremental else "全量"
    logger.info("开始%s抓取微博用户主页", mode)
    return WeiboScraper(incremental=incremental).fetch_and_store()


__all__ = ["WeiboScraper", "run_weibo"]
