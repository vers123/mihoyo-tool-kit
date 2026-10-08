"""Playwright 浏览器会话封装。

统一处理：浏览器启动、上下文创建、Firefox Cookie 注入、页面滚动。
以上下文管理器形式使用::

    with BrowserSession(config) as session:
        session.page.goto(config.url)
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Any

from ..core.exceptions import ScraperError
from ..utils.cookie_loader import load_firefox_cookies
from ..utils.logger import get_module_logger
from .config import ScrapeConfig

if TYPE_CHECKING:  # pragma: no cover
    from playwright.sync_api import Browser, Page, Playwright

logger = get_module_logger("browser")

DEFAULT_BROWSER_ARGS = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]


class BrowserSession:
    """管理 Playwright 生命周期的浏览器会话。"""

    def __init__(self, config: ScrapeConfig) -> None:
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    # ------------------------------------------------------------------ #
    #  属性
    # ------------------------------------------------------------------ #
    @property
    def page(self) -> Page:
        if self._page is None:
            raise ScraperError("浏览器页面尚未初始化，请使用 with 语句")
        return self._page

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise ScraperError("浏览器尚未初始化，请使用 with 语句")
        return self._browser

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #
    def start(self) -> BrowserSession:
        """启动浏览器并创建页面。"""
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        args = list(self.config.browser_args) or list(DEFAULT_BROWSER_ARGS)
        if not self.config.headless:
            args.append("--start-maximized")

        self._browser = self._playwright.chromium.launch(headless=self.config.headless, args=args)
        context = self._browser.new_context(
            user_agent=self.config.user_agent or None, no_viewport=True
        )

        if self.config.use_firefox_cookies and self.config.api_domain_filter:
            self._inject_firefox_cookies(context)

        self._page = context.new_page()
        return self

    def _inject_firefox_cookies(self, context: Any) -> None:
        cookies = load_firefox_cookies(domain_filter=self.config.api_domain_filter)
        if not cookies:
            return
        try:
            context.add_cookies(cookies)
            logger.info(
                "已加载 %d 条 Firefox Cookie (%s)",
                len(cookies),
                self.config.api_domain_filter,
            )
        except Exception as exc:  # pragma: no cover - 依赖浏览器实现
            logger.warning("加载 Cookie 失败: %s", exc)

    def stop(self) -> None:
        """关闭浏览器与 Playwright。"""
        if self._browser is not None:
            try:
                self._browser.close()
            finally:
                self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            finally:
                self._playwright = None
        self._page = None

    def __enter__(self) -> BrowserSession:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    #  页面操作
    # ------------------------------------------------------------------ #
    def goto(self, url: str | None = None) -> None:
        """打开页面并等待网络空闲。"""
        self.page.goto(url or self.config.url, timeout=self.config.timeout)
        with suppress(Exception):  # pragma: no cover - 部分站点永不 idle
            self.page.wait_for_load_state("networkidle")
        time.sleep(self.config.wait_seconds)

    def content(self) -> str:
        """返回当前页面 HTML。"""
        return self.page.content()

    def scroll_to_bottom(
        self,
        *,
        on_tick: Callable[[int], None] | None = None,
        is_stopped: Callable[[], bool] | None = None,
    ) -> int:
        """滚动至底部加载全部内容，返回滚动次数。

        * 无硬上限，依赖「页面高度连续不变」作为终止条件。
        * ``is_stopped`` 由调用方注入（如增量模式命中已存在数据）。
        """
        last_height = self.page.evaluate("document.body.scrollHeight")
        height_unchanged = 0
        scroll_count = 0

        while True:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(self.config.scroll_delay)
            new_height = self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1

            if on_tick is not None:
                on_tick(scroll_count)

            if is_stopped is not None and is_stopped():
                logger.info("滚动提前终止（增量命中）")
                break

            height_unchanged = height_unchanged + 1 if new_height == last_height else 0
            last_height = new_height

            if height_unchanged >= 3:
                break

        logger.info("滚动完成，共 %d 次", scroll_count)
        return scroll_count

    def current_links(self) -> list[str]:
        """返回当前页面匹配选择器的链接。"""
        selector = self.config.url_selector_template
        try:
            return self.page.evaluate(
                "sel => Array.from(document.querySelectorAll(sel)).map(el => el.href)"
                ".filter(Boolean)",
                selector,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("链接检测失败: %s", exc)
            return []


@contextmanager
def open_browser(config: ScrapeConfig) -> Iterator[BrowserSession]:
    """便捷上下文管理器。"""
    session = BrowserSession(config)
    try:
        yield session.start()
    finally:
        session.stop()


__all__ = ["DEFAULT_BROWSER_ARGS", "BrowserSession", "open_browser"]
