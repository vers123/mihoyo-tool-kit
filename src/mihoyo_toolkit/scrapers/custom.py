"""自定义页面抓取器。

移植自 v1 ``fetchers/custom.py``：打开任意 URL、滚动加载并保存 HTML，
文件保存至 ``data/html/<filename>``。
"""

from __future__ import annotations

from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

from ..core.config import get_settings
from ..utils.logger import get_module_logger
from .base import BaseScraper
from .config import ScrapeConfig

logger = get_module_logger("custom")

_settings = get_settings()
_retry = retry(
    stop=stop_after_attempt(_settings.retry.max_attempts),
    wait=wait_fixed(_settings.retry.delay),
    reraise=True,
)


class CustomScraper(BaseScraper[str]):
    """抓取任意页面并保存 HTML。"""

    def __init__(self, url: str, output_filename: str = "custom_page.html") -> None:
        config = ScrapeConfig.from_settings(
            url=url,
            output_filename=output_filename,
            scraper_name="custom",
        )
        super().__init__(config)

    @property
    def name(self) -> str:
        return "custom"

    def extract_items_from_api(self, data: dict[str, Any]) -> list[str]:
        """自定义页面不使用 API 拦截。"""
        return []


@_retry
def run_custom(url: str, filename: str = "custom_page.html") -> None:
    """抓取自定义页面并保存 HTML。"""
    if not url:
        logger.error("请提供要抓取的URL")
        return
    logger.info("抓取自定义页面: %s", url)
    html = CustomScraper(url, filename).run()
    if html:
        logger.info("自定义页面抓取完成")
    else:
        logger.error("自定义页面抓取失败")


__all__ = ["CustomScraper", "run_custom"]
