"""scrapers.config 单元测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mihoyo_toolkit.scrapers.config import ScrapeConfig


def test_from_settings_uses_global_defaults(settings) -> None:
    config = ScrapeConfig.from_settings("https://example.com", "page.html")
    assert config.url == "https://example.com"
    assert config.output_filename == "page.html"
    assert config.headless == settings.fetch.headless
    assert config.wait_seconds == settings.fetch.wait_seconds
    assert config.timeout == settings.fetch.timeout
    assert config.user_agent == settings.fetch.user_agent
    assert config.browser_args == list(settings.fetch.browser_args)
    assert config.scroll_delay == settings.fetch.scroll_delay
    assert config.incremental_mode == settings.incremental.enabled
    assert config.use_firefox_cookies == settings.cookies.use_firefox
    assert config.existing_urls == set()


def test_from_settings_overrides() -> None:
    config = ScrapeConfig.from_settings(
        "https://example.com",
        "page.html",
        headless=False,
        scraper_name="demo",
        existing_urls={"https://a"},
    )
    assert config.headless is False
    assert config.scraper_name == "demo"
    assert config.existing_urls == {"https://a"}


def test_required_fields() -> None:
    with pytest.raises(ValidationError):
        ScrapeConfig(output_filename="x")
