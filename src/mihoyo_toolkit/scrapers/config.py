"""抓取器运行配置。

将原 ``ScraperConfig`` 迁移为 pydantic 模型，并从全局 :class:`ToolkitSettings`
提供默认值。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..core.config import get_settings


class ScrapeConfig(BaseModel):
    """单次抓取任务的配置。"""

    url: str
    output_filename: str
    #: HTML 保存子目录（相对 ``<root>/data/html``；空串表示直接放在 ``html`` 下）
    html_subdir: str = ""
    #: 抓取器名（用于 HAR 目录与日志前缀）
    scraper_name: str = ""

    headless: bool = True
    wait_seconds: float = 3.0
    timeout: int = 120_000
    user_agent: str = ""
    browser_args: list[str] = Field(default_factory=list)
    scroll_delay: float = 2.0

    #: 增量模式
    incremental_mode: bool = False
    existing_urls: set[str] = Field(default_factory=set)

    #: API 拦截配置
    api_url_keywords: list[str] = Field(default_factory=list)
    api_domain_filter: str = ""
    use_firefox_cookies: bool = False

    #: 用于检测新 URL 的选择器（滚动时增量判断）
    url_selector_template: str = "a[href*='/article/'], a[href*='/news/']"

    @classmethod
    def from_settings(cls, url: str, output_filename: str, **overrides: object) -> ScrapeConfig:
        """基于全局配置构建，允许局部覆盖。"""
        s = get_settings()
        base: dict[str, object] = {
            "url": url,
            "output_filename": output_filename,
            "headless": s.fetch.headless,
            "wait_seconds": s.fetch.wait_seconds,
            "timeout": s.fetch.timeout,
            "user_agent": s.fetch.user_agent,
            "browser_args": list(s.fetch.browser_args),
            "scroll_delay": s.fetch.scroll_delay,
            "incremental_mode": s.incremental.enabled,
            "use_firefox_cookies": s.cookies.use_firefox,
        }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]


__all__ = ["ScrapeConfig"]
