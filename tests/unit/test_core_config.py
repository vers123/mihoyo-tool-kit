"""core.config 单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from mihoyo_toolkit.core.config import (
    BackupSettings,
    NewsSiteSource,
    RetrySettings,
    ToolkitSettings,
    get_settings,
    load_settings,
    reload_settings,
)


def test_get_settings_reads_tmp_config(settings: ToolkitSettings) -> None:
    assert settings.app.mode == "cli"
    assert settings.fetch.user_agent == "mihoyo-toolkit-test-agent"
    assert settings.retry.max_attempts == 2
    assert settings.cookies.use_firefox is False


def test_news_sources_keys_and_get_site(settings: ToolkitSettings) -> None:
    keys = settings.sources.news.keys()
    assert keys == ["genshin", "genshin_en", "zzz", "starrail"]

    site = settings.sources.news.get_site("genshin")
    assert site.label == "原神"
    assert site.api_chan_id == "719"


def test_get_site_invalid_key_raises(settings: ToolkitSettings) -> None:
    with pytest.raises(KeyError):
        settings.sources.news.get_site("honkai")


def test_detail_url_formatting(settings: ToolkitSettings) -> None:
    site = settings.sources.news.get_site("genshin")
    assert site.detail_url(123) == "/main/news/detail/123"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_reload_settings(monkeypatch) -> None:
    monkeypatch.setenv("MIHOYO_FETCH__HEADLESS", "false")
    monkeypatch.setenv("MIHOYO_RETRY__MAX_ATTEMPTS", "5")
    reloaded = reload_settings()
    assert reloaded.fetch.headless is False
    assert reloaded.retry.max_attempts == 5


def test_load_settings_from_custom_file(tmp_path: Path) -> None:
    cfg = tmp_path / "alt.toml"
    cfg.write_text(
        """
[fetch]
headless = false

[sources.user]
url = "https://example.com/u"

[sources.baike]
url = "https://example.com/b"

[sources.weibo]
url = "https://example.com/w"

[sources.news.genshin]
url = "https://example.com/news"
label = "原神"
scraper = "news_genshin"
api_base_url = "https://example.com/api"
api_chan_id = "1"
detail_url_pattern = "/news/{iInfoId}"

[sources.news.genshin_en]
url = "https://example.com/news-en"
label = "原神EN"
scraper = "news_genshin_en"
api_base_url = "https://example.com/api-en"
api_chan_id = "2"
detail_url_pattern = "/en/{iInfoId}"

[sources.news.zzz]
url = "https://example.com/zzz"
label = "绝区零"
scraper = "news_zzz"
api_base_url = "https://example.com/api-zzz"
api_chan_id = "3"
detail_url_pattern = "/news/{iInfoId}"

[sources.news.starrail]
url = "https://example.com/sr"
label = "星穹铁道"
scraper = "news_starrail"
api_base_url = "https://example.com/api-sr"
api_chan_id = "4"
detail_url_pattern = "/news/{iInfoId}"
""",
        encoding="utf-8",
    )
    loaded = load_settings(cfg)
    assert loaded.fetch.headless is False
    assert loaded.sources.user.url == "https://example.com/u"


def test_load_settings_none_returns_cached() -> None:
    assert load_settings(None) is get_settings()


def test_news_site_source_requires_fields() -> None:
    with pytest.raises(ValidationError):
        NewsSiteSource(url="https://x", label="x")


def test_retry_settings_constraints() -> None:
    with pytest.raises(ValidationError):
        RetrySettings(max_attempts=0)


def test_backup_settings_constraints() -> None:
    with pytest.raises(ValidationError):
        BackupSettings(max_backups=0)
