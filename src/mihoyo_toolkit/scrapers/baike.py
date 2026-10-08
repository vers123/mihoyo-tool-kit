"""角色图鉴抓取器。

移植自 v1 ``fetchers/baike.py`` + ``extractors/images.py``：

* 抓取米哈游角色图鉴页面（HTML 保存为 ``baike_characters.html``）；
* 从 HTML 解析角色头像图片链接，落库到 ``images`` 表（不再写 TXT）。
"""

from __future__ import annotations

import re
from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

from ..core.config import get_settings
from ..core.models import ImageItem
from ..core.storage import Storage
from ..utils.logger import get_module_logger
from .base import BaseScraper
from .config import ScrapeConfig

logger = get_module_logger("baike")

_settings = get_settings()
_retry = retry(
    stop=stop_after_attempt(_settings.retry.max_attempts),
    wait=wait_fixed(_settings.retry.delay),
    reraise=True,
)

_IMAGE_PATTERN = re.compile(
    r'class="collection-avatar__item".*?'
    r'data-src="(https://.*?mihoyo\.com/.*?\.\w+)\?.*?"'
    r".*?"
    r'class="collection-avatar__title">(.*?)</div>',
    re.DOTALL,
)


class BaikeScraper(BaseScraper[ImageItem]):
    """角色图鉴抓取器（DOM 解析）。"""

    def __init__(self) -> None:
        settings = get_settings()
        config = ScrapeConfig.from_settings(
            url=settings.sources.baike.url,
            output_filename="baike_characters.html",
            scraper_name="baike",
        )
        super().__init__(config)

    @property
    def name(self) -> str:
        return "baike"

    def extract_items_from_api(self, data: dict[str, Any]) -> list[ImageItem]:
        """图鉴页面不使用 API 拦截。"""
        return []

    def parse(self, html: str) -> list[ImageItem]:
        """从 HTML 解析角色头像图片链接。"""
        items: list[ImageItem] = []
        for img_url, name in _IMAGE_PATTERN.findall(html):
            items.append(ImageItem(character_id="", name=name.strip(), image_url=img_url))
        items.reverse()
        return items


@_retry
def run_baike() -> int:
    """抓取角色图鉴页面并落库，返回新增图片条数。"""
    logger.info("开始抓取角色图鉴页面")
    scraper = BaikeScraper()
    html = scraper.run()
    items = scraper.parse(html)
    if not items:
        logger.warning("未解析到图鉴图片数据")
        return 0
    with Storage() as store:
        new = store.upsert_images(items)
    logger.info("图鉴抓取 %d 个图片链接，新增 %d 条", len(items), new)
    return new


__all__ = ["BaikeScraper", "run_baike"]
