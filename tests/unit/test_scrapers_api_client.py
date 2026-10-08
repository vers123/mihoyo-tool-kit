"""scrapers.api_client 单元测试。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from mihoyo_toolkit.core.exceptions import ParseError
from mihoyo_toolkit.scrapers.api_client import (
    MiHoYoApiClient,
    fetch_all_games,
    fetch_all_games_async,
)


def _entry(info_id: int, title: str = "标题", ext: dict | None = None) -> dict[str, Any]:
    return {
        "iInfoId": info_id,
        "sTitle": title,
        "dtStartTime": "2024-01-01 10:00:00",
        "sCategoryName": "公告",
        "sIntro": "摘要",
        "sExt": json.dumps(ext) if ext is not None else "",
    }


def test_build_page_url_contains_params() -> None:
    client = MiHoYoApiClient("genshin")
    url = client.build_page_url(2)
    assert url.startswith("https://act-api-takumi-static.mihoyo.com")
    assert "iPage=2" in url
    assert "iPageSize=2" in url
    assert "iChanId=719" in url
    assert "sLangKey=zh-cn" in url


def test_build_page_url_includes_app_id() -> None:
    client = MiHoYoApiClient("genshin_en")
    assert "iAppId=32" in client.build_page_url(1)


def test_headers() -> None:
    client = MiHoYoApiClient("genshin")
    headers = client.headers()
    assert headers["Accept"] == "application/json"
    assert headers["Referer"] == "https://ys.mihoyo.com/main/news"
    assert headers["User-Agent"]


def test_extract_items_valid() -> None:
    client = MiHoYoApiClient("genshin")
    data = {"data": {"list": [_entry(1, "a"), _entry(2, "b")]}}
    items = client.extract_items(data)
    assert [i.iInfoId for i in items] == [1, 2]
    assert all(i.game == "genshin" for i in items)
    assert items[0].url.startswith("https://ys.mihoyo.com/main/news/detail/1")


def test_extract_items_filters_invalid_entries() -> None:
    client = MiHoYoApiClient("genshin")
    data = {
        "data": {
            "list": [
                _entry(1),
                "not-a-dict",
                {"iInfoId": "", "sTitle": "no-id"},
                {"iInfoId": 3, "sTitle": ""},
            ]
        }
    }
    items = client.extract_items(data)
    assert [i.iInfoId for i in items] == [1]


def test_extract_items_non_dict_raises() -> None:
    client = MiHoYoApiClient("genshin")
    with pytest.raises(ParseError):
        client.extract_items(["bad"])  # type: ignore[arg-type]


def test_extract_items_list_not_a_list() -> None:
    client = MiHoYoApiClient("genshin")
    assert client.extract_items({"data": {"list": "oops"}}) == []


def test_extract_poster_url_variants() -> None:
    client = MiHoYoApiClient("genshin")
    assert client._extract_poster_url(_entry(1, ext={"720_1": [{"url": "https://x/p.png"}]})) == (
        "https://x/p.png"
    )
    assert client._extract_poster_url(_entry(2, ext={"720_1": {"url": "https://x/q.png"}})) == (
        "https://x/q.png"
    )
    assert client._extract_poster_url({"sExt": "{invalid json"}) == ""
    assert client._extract_poster_url({"sExt": json.dumps({"other": "v"})}) == ""
    assert client._extract_poster_url({"sExt": ""}) == ""


def test_make_full_url() -> None:
    client = MiHoYoApiClient("genshin")
    assert client._make_full_url("https://already.example.com/x") == "https://already.example.com/x"
    assert (
        client._make_full_url("/main/news/detail/9") == "https://ys.mihoyo.com/main/news/detail/9"
    )


def test_fetch_all_paginates(monkeypatch) -> None:
    pages = {
        1: {"data": {"iTotal": 3, "list": [_entry(1), _entry(2)]}},
        2: {"data": {"iTotal": 3, "list": [_entry(3)]}},
    }

    def fake_get_page(self, client, page):
        return pages.get(page, {"data": {"list": []}})

    monkeypatch.setattr(MiHoYoApiClient, "_get_page", fake_get_page)
    items = MiHoYoApiClient("genshin").fetch_all()
    assert [i.iInfoId for i in items] == [1, 2, 3]


def test_fetch_all_single_page(monkeypatch) -> None:
    def fake_get_page(self, client, page):
        return {"data": {"list": [_entry(1)]}}

    monkeypatch.setattr(MiHoYoApiClient, "_get_page", fake_get_page)
    assert len(MiHoYoApiClient("genshin").fetch_all()) == 1


def test_fetch_all_first_page_error_returns_empty(monkeypatch) -> None:
    def fake_get_page(self, client, page):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(MiHoYoApiClient, "_get_page", fake_get_page)
    assert MiHoYoApiClient("genshin").fetch_all() == []


def test_fetch_all_later_page_error_breaks(monkeypatch) -> None:
    def fake_get_page(self, client, page):
        if page == 1:
            return {"data": {"iTotal": 10, "list": [_entry(1), _entry(2)]}}
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(MiHoYoApiClient, "_get_page", fake_get_page)
    assert len(MiHoYoApiClient("genshin").fetch_all()) == 2


def test_fetch_all_stops_on_existing(monkeypatch) -> None:
    called = {"pages": 0}

    def fake_get_page(self, client, page):
        called["pages"] += 1
        return {"data": {"iTotal": 10, "list": [_entry(1), _entry(2)]}}

    monkeypatch.setattr(MiHoYoApiClient, "_get_page", fake_get_page)
    client = MiHoYoApiClient(
        "genshin",
        incremental=True,
        existing_urls={"https://ys.mihoyo.com/main/news/detail/1"},
    )
    items = client.fetch_all()
    assert called["pages"] == 1
    assert len(items) == 2


def test_should_stop_disabled_without_incremental() -> None:
    client = MiHoYoApiClient("genshin")
    item = client.extract_items({"data": {"list": [_entry(1)]}})[0]
    assert client._should_stop([item]) is False


def test_fetch_all_async(monkeypatch) -> None:
    async def fake_get_page_async(self, client, page):
        return {"data": {"iTotal": 1, "list": [_entry(1)]}}

    monkeypatch.setattr(MiHoYoApiClient, "_get_page_async", fake_get_page_async)
    items = asyncio.run(MiHoYoApiClient("genshin").fetch_all_async())
    assert [i.iInfoId for i in items] == [1]


def test_fetch_all_async_error(monkeypatch) -> None:
    async def fake_get_page_async(self, client, page):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(MiHoYoApiClient, "_get_page_async", fake_get_page_async)
    assert asyncio.run(MiHoYoApiClient("genshin").fetch_all_async()) == []


def test_fetch_all_games(monkeypatch) -> None:
    monkeypatch.setattr(MiHoYoApiClient, "fetch_all", lambda self: [])
    result = fetch_all_games(["genshin", "zzz"])
    assert result == {"genshin": [], "zzz": []}


def test_fetch_all_games_defaults_to_all_sites(monkeypatch) -> None:
    monkeypatch.setattr(MiHoYoApiClient, "fetch_all", lambda self: [])
    result = fetch_all_games()
    assert set(result) == {"genshin", "genshin_en", "zzz", "starrail"}


def test_fetch_all_games_async(monkeypatch) -> None:
    async def fake_fetch(self):
        return []

    monkeypatch.setattr(MiHoYoApiClient, "fetch_all_async", fake_fetch)
    result = asyncio.run(fetch_all_games_async(["genshin"]))
    assert result == {"genshin": []}
