"""四站点新闻抓取器注册表与流程集成测试（网络打桩）。"""

from __future__ import annotations

import pytest

from mihoyo_toolkit.core.models import NewsItem
from mihoyo_toolkit.scrapers.api_client import MiHoYoApiClient
from mihoyo_toolkit.scrapers.news import (
    NEWS_SCRAPERS,
    GameNewsScraper,
    GenshinENNewsScraper,
    GenshinNewsScraper,
    SRNewsScraper,
    ZZZNewsScraper,
    get_scraper,
    run_all_news,
    run_news,
    run_news_genshin,
    run_news_genshin_en,
    run_news_starrail,
    run_news_zzz,
)

NEWS_KEYS = {"genshin", "genshin_en", "zzz", "starrail"}


def _item(game: str = "genshin", info_id: int = 1) -> NewsItem:
    return NewsItem(
        game=game,
        iInfoId=info_id,
        sTitle="标题",
        dtStartTime="2024-01-01 10:00:00",
        sCategoryName="公告",
        sIntro="摘要",
        url=f"https://ys.mihoyo.com/main/news/detail/{info_id}",
    )


def test_registry_contains_four_sites() -> None:
    assert set(NEWS_SCRAPERS) == NEWS_KEYS
    assert NEWS_SCRAPERS["genshin"] is GenshinNewsScraper
    assert NEWS_SCRAPERS["genshin_en"] is GenshinENNewsScraper
    assert NEWS_SCRAPERS["zzz"] is ZZZNewsScraper
    assert NEWS_SCRAPERS["starrail"] is SRNewsScraper


def test_get_scraper_known_and_unknown() -> None:
    assert get_scraper("zzz") is ZZZNewsScraper
    with pytest.raises(KeyError):
        get_scraper("unknown")


@pytest.mark.parametrize("game", sorted(NEWS_KEYS))
def test_scraper_metadata(game: str, settings) -> None:
    cls = get_scraper(game)
    scraper = cls(game, incremental=False)
    assert scraper.html_filename == f"{game}_news.html"
    assert scraper.name == settings.sources.news.get_site(game).scraper
    assert scraper.game == game


def test_extract_items_from_api() -> None:
    scraper = GenshinNewsScraper("genshin", incremental=False)
    data = {
        "data": {
            "list": [
                {
                    "iInfoId": 1,
                    "sTitle": "标题",
                    "dtStartTime": "2024-01-01 10:00:00",
                    "sCategoryName": "公告",
                    "sIntro": "摘要",
                }
            ]
        }
    }
    items = scraper.extract_items_from_api(data)
    assert [i.iInfoId for i in items] == [1]
    # 非法响应被防御性捕获
    assert scraper.extract_items_from_api(["bad"]) == []


def test_fetch_uses_api(monkeypatch) -> None:
    items = [_item()]
    monkeypatch.setattr(MiHoYoApiClient, "fetch_all", lambda self: items)
    scraper = GenshinNewsScraper("genshin", incremental=False)
    assert scraper.fetch() == items


def test_fetch_returns_empty_without_fallback(monkeypatch) -> None:
    monkeypatch.setattr(MiHoYoApiClient, "fetch_all", lambda self: [])
    scraper = GenshinNewsScraper("genshin", incremental=False)
    monkeypatch.setattr(scraper, "run", lambda **_kwargs: "<html>")
    assert scraper.fetch() == []


def test_fetch_falls_back_to_har(monkeypatch, har_factory) -> None:
    har_factory("news_genshin")
    monkeypatch.setattr(MiHoYoApiClient, "fetch_all", lambda self: [])
    scraper = GenshinNewsScraper("genshin", incremental=False)
    monkeypatch.setattr(scraper, "run", lambda **_kwargs: "<html>")

    items = scraper.fetch()
    assert [i.iInfoId for i in items] == [1001, 1002]


def test_fetch_and_store(store, monkeypatch) -> None:
    scraper = GenshinNewsScraper("genshin", incremental=False)
    monkeypatch.setattr(scraper, "fetch", lambda: [_item(info_id=1), _item(info_id=2)])
    assert scraper.fetch_and_store() == 2
    assert store.count_news("genshin") == 2


def test_fetch_and_store_no_items(monkeypatch) -> None:
    scraper = GenshinNewsScraper("genshin", incremental=False)
    monkeypatch.setattr(scraper, "fetch", lambda: [])
    assert scraper.fetch_and_store() == 0


def test_incremental_constructor_reads_existing_urls(store, sample_news_items) -> None:
    store.upsert_news("genshin", sample_news_items)
    scraper = GameNewsScraper("genshin", incremental=True)
    assert scraper.config.existing_urls == {
        "https://ys.mihoyo.com/main/news/detail/1001",
        "https://ys.mihoyo.com/main/news/detail/1002",
    }


def test_base_requires_game() -> None:
    with pytest.raises(ValueError):
        GameNewsScraper()


def test_run_news(monkeypatch) -> None:
    monkeypatch.setattr(GenshinNewsScraper, "fetch_and_store", lambda self: 5)
    assert run_news("genshin", incremental=False) == 5


def test_run_all_news(monkeypatch) -> None:
    monkeypatch.setattr(GameNewsScraper, "fetch_and_store", lambda self: 1)
    result = run_all_news(incremental=False)
    assert set(result) == NEWS_KEYS
    assert all(value == 1 for value in result.values())


@pytest.mark.parametrize(
    ("func", "attr"),
    [
        (run_news_genshin, GenshinNewsScraper),
        (run_news_genshin_en, GenshinENNewsScraper),
        (run_news_zzz, ZZZNewsScraper),
        (run_news_starrail, SRNewsScraper),
    ],
)
def test_run_news_convenience(monkeypatch, func, attr) -> None:
    monkeypatch.setattr(attr, "fetch_and_store", lambda self: 3)
    assert func(incremental=False) == 3
