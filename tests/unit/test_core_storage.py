"""core.storage 单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mihoyo_toolkit.core.exceptions import StorageError
from mihoyo_toolkit.core.models import (
    ImageItem,
    NewsItem,
    PostItem,
    TutorialItem,
    WeiboItem,
)
from mihoyo_toolkit.core.storage import Storage


def _news(game: str, info_id: int, start: str, title: str = "t") -> NewsItem:
    return NewsItem(
        game=game,
        iInfoId=info_id,
        sTitle=title,
        dtStartTime=start,
        sCategoryName="cat",
        sIntro="intro",
        poster_url="https://example.com/p.png",
        url=f"https://example.com/{game}/{info_id}",
        raw={"iInfoId": info_id},
    )


def test_db_path_default_uses_path_manager(store: Storage) -> None:
    from mihoyo_toolkit.core.paths import get_path_manager

    assert store.db_path == get_path_manager().db


def test_custom_db_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom" / "db.sqlite"
    with Storage(custom) as s:
        assert s.db_path == custom
        assert s.count_news() == 0
    assert custom.is_file()


def test_connect_is_idempotent(store: Storage) -> None:
    conn = store.connect()
    assert store.connect() is conn


def test_context_manager_closes_connection(tmp_path: Path) -> None:
    with Storage(tmp_path / "x.db") as s:
        s.connect()
        assert s._conn is not None
    assert s._conn is None


def test_upsert_news_returns_new_count_and_dedupes(store: Storage) -> None:
    items = [_news("genshin", 1, "2024-01-01 00:00:00"), _news("genshin", 2, "2024-01-02 00:00:00")]
    assert store.upsert_news("genshin", items) == 2
    # 幂等：再次写入不新增
    assert store.upsert_news("genshin", items) == 0


def test_upsert_news_empty_returns_zero(store: Storage) -> None:
    assert store.upsert_news("genshin", []) == 0


def test_get_existing_urls_and_info_ids(store: Storage) -> None:
    store.upsert_news("genshin", [_news("genshin", 1, "2024-01-01 00:00:00")])
    store.upsert_news("zzz", [_news("zzz", 5, "2024-01-03 00:00:00")])
    assert store.get_existing_urls("genshin") == {"https://example.com/genshin/1"}
    assert store.get_existing_info_ids("genshin") == {1}
    assert store.get_existing_info_ids("zzz") == {5}


def test_count_news_and_count_all(store: Storage) -> None:
    store.upsert_news("genshin", [_news("genshin", 1, "2024-01-01 00:00:00")])
    store.upsert_news("zzz", [_news("zzz", 1, "2024-01-01 00:00:00")])
    store.upsert_news("zzz", [_news("zzz", 2, "2024-01-02 00:00:00")])
    assert store.count_news("genshin") == 1
    assert store.count_news() == 3
    assert store.count_all() == {"genshin": 1, "zzz": 2}


def test_query_news_ordering_and_limit(store: Storage) -> None:
    store.upsert_news(
        "genshin",
        [
            _news("genshin", 1, "2024-01-01 00:00:00", "a"),
            _news("genshin", 2, "2024-01-03 00:00:00", "b"),
            _news("genshin", 3, "2024-01-02 00:00:00", "c"),
        ],
    )
    desc = store.query_news("genshin")
    assert [item.sTitle for item in desc] == ["b", "c", "a"]

    asc = store.query_news("genshin", ascending=True)
    assert [item.sTitle for item in asc] == ["a", "c", "b"]

    limited = store.query_news("genshin", limit=2)
    assert len(limited) == 2

    assert store.query_news("zzz") == []
    assert len(store.query_news()) == 3


def test_query_news_restores_raw(store: Storage) -> None:
    store.upsert_news("genshin", [_news("genshin", 1, "2024-01-01 00:00:00")])
    item = store.query_news("genshin")[0]
    assert item.raw == {"iInfoId": 1}


def test_query_news_handles_invalid_raw_json(store: Storage) -> None:
    conn = store.connect()
    conn.execute(
        "INSERT INTO news (game, info_id, title, start_time, url, raw) VALUES (?, ?, ?, ?, ?, ?)",
        ("genshin", 7, "bad", "2024-01-01 00:00:00", "https://example.com/bad", "not-json"),
    )
    conn.commit()
    item = store.query_news("genshin", limit=1)[0]
    assert item.raw == {}


def test_upsert_posts_and_query(store: Storage) -> None:
    posts = [
        PostItem(post_id="p1", title="t1", created_at="2024-01-01", url="u1", content="c1"),
        PostItem(post_id="p2", title="t2", created_at="2024-01-02", url="u2"),
    ]
    assert store.upsert_posts(posts) == 2
    assert store.upsert_posts(posts) == 0
    assert store.upsert_posts([]) == 0

    desc = store.query_posts()
    assert [p.post_id for p in desc] == ["p2", "p1"]
    assert store.query_posts(ascending=True)[0].post_id == "p1"
    assert len(store.query_posts(limit=1)) == 1
    assert store.get_existing_post_ids() == {"p1", "p2"}


def test_upsert_weibo_and_query(store: Storage) -> None:
    items = [
        WeiboItem(post_id="w1", text="a", created_at="2024-01-01", url="u1", reposts=1),
        WeiboItem(post_id="w2", text="b", created_at="2024-01-02", url="u2", comments=3),
    ]
    assert store.upsert_weibo(items) == 2
    assert store.upsert_weibo(items) == 0
    desc = store.query_weibo()
    assert [w.post_id for w in desc] == ["w2", "w1"]
    assert desc[0].comments == 3
    assert store.query_weibo(ascending=True)[0].post_id == "w1"
    assert len(store.query_weibo(limit=1)) == 1
    assert store.get_existing_weibo_ids() == {"w1", "w2"}


def test_upsert_tutorial_and_count(store: Storage) -> None:
    items = [
        TutorialItem(character_id="c1", name="n1", lang="zh-cn"),
        TutorialItem(character_id="c2", name="n2", lang="en-us"),
    ]
    assert store.upsert_tutorial(items) == 2
    assert store.upsert_tutorial(items) == 0
    assert store.upsert_tutorial([]) == 0
    assert store.count_table("tutorial") == 2


def test_upsert_images_and_query(store: Storage) -> None:
    items = [
        ImageItem(character_id="c1", name="n1", image_url="https://x/1.png"),
        ImageItem(character_id="c2", name="n2", image_url="https://x/2.png"),
    ]
    assert store.upsert_images(items) == 2
    assert store.upsert_images(items) == 0
    assert store.upsert_images([]) == 0
    images = store.query_images()
    assert [i.image_url for i in images] == ["https://x/1.png", "https://x/2.png"]


def test_count_table_known_and_unknown(store: Storage) -> None:
    assert store.count_table("news") == 0
    assert store.count_table("posts") == 0
    assert store.count_table("weibo") == 0
    assert store.count_table("images") == 0
    with pytest.raises(StorageError):
        store.count_table("not_a_table")


def test_vacuum_runs(store: Storage) -> None:
    store.upsert_news("genshin", [_news("genshin", 1, "2024-01-01 00:00:00")])
    store.vacuum()
    assert store.count_news() == 1


def test_clear_by_game_and_all(store: Storage) -> None:
    store.upsert_news("genshin", [_news("genshin", 1, "2024-01-01 00:00:00")])
    store.upsert_news("zzz", [_news("zzz", 1, "2024-01-01 00:00:00")])
    assert store.clear("genshin") == 1
    assert store.count_news() == 1
    assert store.clear() == 1
    assert store.count_news() == 0
