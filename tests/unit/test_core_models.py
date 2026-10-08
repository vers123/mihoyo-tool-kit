"""core.models 单元测试。"""

from __future__ import annotations

from datetime import datetime

from mihoyo_toolkit.core.models import (
    ENTITY_TABLES,
    ChangelogEntry,
    ImageItem,
    NewsItem,
    PostItem,
    TutorialItem,
    WeiboItem,
)


def _news(**kwargs) -> NewsItem:
    base = {
        "game": "genshin",
        "iInfoId": 1,
        "sTitle": "t",
        "url": "https://example.com/1",
    }
    base.update(kwargs)
    return NewsItem(**base)


def test_news_item_snake_case_aliases() -> None:
    item = _news(dtStartTime="2024-01-01 00:00:00", sCategoryName="公告", sIntro="摘要")
    assert item.info_id == 1
    assert item.title == "t"
    assert item.start_time == "2024-01-01 00:00:00"
    assert item.category == "公告"
    assert item.intro == "摘要"


def test_news_item_sort_key() -> None:
    item = _news(dtStartTime="2024-01-01 00:00:00", iInfoId=9)
    assert item.sort_key() == ("2024-01-01 00:00:00", 9)


def test_news_item_coerces_datetime() -> None:
    item = _news(dtStartTime=datetime(2024, 5, 6, 7, 8, 9))
    assert item.dtStartTime == "2024-05-06 07:08:09"


def test_news_item_coerces_none_and_non_str() -> None:
    assert _news(dtStartTime=None).dtStartTime == ""
    assert _news(dtStartTime=12345).dtStartTime == "12345"


def test_news_item_raw_default_is_isolated() -> None:
    a = _news()
    b = _news()
    a.raw["k"] = "v"
    assert b.raw == {}


def test_post_item_sort_key() -> None:
    item = PostItem(post_id="p1", created_at="2024-01-01")
    assert item.sort_key == "2024-01-01"


def test_weibo_item_fields_and_sort_key() -> None:
    item = WeiboItem(
        post_id="w1", text="hi", created_at="2024-02-02", reposts=1, comments=2, attitudes=3
    )
    assert item.sort_key == "2024-02-02"
    assert (item.reposts, item.comments, item.attitudes) == (1, 2, 3)


def test_tutorial_item_sort_key() -> None:
    assert TutorialItem(character_id="c1", name="n").sort_key == "c1"


def test_image_item_sort_key() -> None:
    assert ImageItem(image_url="https://x/y.png").sort_key == "https://x/y.png"


def test_changelog_entry_sort_key() -> None:
    assert ChangelogEntry(version="1.0", date="2024-01-01").sort_key == "2024-01-01"


def test_entity_tables_mapping() -> None:
    assert ENTITY_TABLES["news"] == "news"
    assert ENTITY_TABLES["post"] == "posts"
    assert ENTITY_TABLES["weibo"] == "weibo"
    assert ENTITY_TABLES["tutorial"] == "tutorial"
    assert ENTITY_TABLES["image"] == "images"
