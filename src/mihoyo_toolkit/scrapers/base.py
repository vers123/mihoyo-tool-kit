"""抓取器抽象基类。

提供 Playwright 抓取通用能力：

* 浏览器会话管理（委托 :class:`BrowserSession`）
* API 响应拦截（``page.on("response")``）
* 滚动加载 + 增量提前终止
* HAR 文件回退

子类需实现 :meth:`extract_items_from_api`（拦截解析）或 :meth:`parse`（HTML 解析）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from ..core.paths import get_path_manager
from ..utils.har_loader import find_har_file, print_har_instructions
from ..utils.logger import get_module_logger
from .browser import BrowserSession
from .config import ScrapeConfig

T = TypeVar("T")

logger = get_module_logger("scraper")


class BaseScraper(ABC, Generic[T]):
    """抓取器基类。

    ``T`` 为解析结果的元素类型（如 :class:`NewsItem`）。
    """

    def __init__(self, config: ScrapeConfig) -> None:
        self.config = config
        self.html_path = get_path_manager().html / config.output_filename
        self._api_items: list[Any] = []
        self._stop_requested = False

    # ------------------------------------------------------------------ #
    #  子类契约
    # ------------------------------------------------------------------ #
    @property
    @abstractmethod
    def name(self) -> str:
        """抓取器名称（用于日志与 HAR 目录）。"""

    @abstractmethod
    def extract_items_from_api(self, data: dict[str, Any]) -> list[Any]:
        """从拦截到的 API JSON 响应提取条目。"""

    def parse(self, html: str) -> list[T]:
        """从 HTML 解析条目（不使用 API 拦截时必须实现）。"""
        raise NotImplementedError("未使用 API 拦截的子类必须实现 parse")

    # ------------------------------------------------------------------ #
    #  API 拦截
    # ------------------------------------------------------------------ #
    def setup_api_interception(self, session: BrowserSession) -> None:
        """注册 API 响应拦截。"""
        self._api_items = []
        self._stop_requested = False
        keywords = self.config.api_url_keywords

        def handle_response(response: Any) -> None:
            if not response.ok:
                return
            if keywords and not any(kw in response.url for kw in keywords):
                return
            try:
                data = response.json()
            except Exception:
                return
            items = self.extract_items_from_api(data)
            if not items:
                return
            self._api_items.extend(items)
            logger.info("拦截到 API 响应: +%d 条（共 %d 条）", len(items), len(self._api_items))
            if self._should_stop(items):
                logger.info("发现已存在数据，增量模式停止")
                self._stop_requested = True

        session.page.on("response", handle_response)

    def _should_stop(self, items: list[Any]) -> bool:
        if not (
            self.config.incremental_mode
            and self.config.existing_urls
            and self._settings_stop_on_existing()
        ):
            return False
        return any(
            (url := self._item_url(item)) and url in self.config.existing_urls for item in items
        )

    @staticmethod
    def _settings_stop_on_existing() -> bool:
        from ..core.config import get_settings

        return get_settings().incremental.stop_on_existing

    @staticmethod
    def _item_url(item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("url", ""))
        return str(getattr(item, "url", ""))

    # ------------------------------------------------------------------ #
    #  主流程
    # ------------------------------------------------------------------ #
    def run(self, *, on_progress: Callable[[int], None] | None = None) -> str:
        """执行抓取：打开页面 → 拦截 API → 滚动 → 保存 HTML。返回 HTML。"""
        logger.info("启动抓取: %s (%s)", self.config.url, self.name)
        with BrowserSession(self.config) as session:
            self.setup_api_interception(session)
            session.goto()
            html = self._process_page(session, on_progress=on_progress)
            self.save_html(html)
        return html

    def _process_page(
        self, session: BrowserSession, *, on_progress: Callable[[int], None] | None = None
    ) -> str:
        session.scroll_to_bottom(
            on_tick=on_progress,
            is_stopped=lambda: self._stop_requested,
        )
        return session.content()

    def save_html(self, html: str) -> None:
        """保存 HTML 至 ``data/html/<output_filename>``。"""
        self.html_path.parent.mkdir(parents=True, exist_ok=True)
        self.html_path.write_text(html, encoding="utf-8")
        logger.info("已保存 HTML: %s", get_path_manager().relative(self.html_path))

    # ------------------------------------------------------------------ #
    #  HAR 回退
    # ------------------------------------------------------------------ #
    def check_api_or_har(self) -> str | None:
        """检查 API 拦截结果；无数据时尝试 HAR 回退。

        Returns:
            ``"use_har"`` 表示应使用 HAR 文件重试；``None`` 表示无可用回退。
        """
        if self._api_items:
            return None
        logger.warning("自动检测 API 未获取到数据")
        if not self.config.scraper_name:
            return None

        har_path = find_har_file(self.config.scraper_name)
        if har_path:
            logger.info("检测到 HAR 文件: %s", har_path)
            return "use_har"

        domains = (
            self.config.api_domain_filter.split(",") if self.config.api_domain_filter else None
        )
        print_har_instructions(self.config.scraper_name, self.config.url, domains)
        return None


__all__ = ["BaseScraper"]
