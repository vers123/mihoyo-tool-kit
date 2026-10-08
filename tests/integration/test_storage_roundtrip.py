"""存储层往返集成测试（真实 SQLite 文件）。"""

from __future__ import annotations

from pathlib import Path

from mihoyo_toolkit.core.models import ImageItem, NewsItem, PostItem, TutorialItem, WeiboItem
from mihoyo_toolkit.core.paths import get_path_manager
from mihoyo_toolkit.core.storage import Storage


def test_news_roundtrip_persists_to_tmp_db(
    store: Storage, sample_news_items, tmp_home: Path
) -> None:
    inserted = store.upsert_news("genshin", sample_news_items)
    assert inserted == 2

    # 数据库落在临时项目根内，不污染仓库
    db_path = get_path_manager().db
    assert db_path.is_file()
    assert tmp_home in db_path.parents

    # 新连接可见已提交数据
    with Storage() as reopened:
        items = reopened.query_news("genshin")
        assert {item.sTitle for item in items} == {"版本更新说明", "新角色预告"}
        assert reopened.count_all() == {"genshin": 2}
        assert reopened.get_existing_info_ids("genshin") == {1001, 1002}


def test_wal_mode_enabled(store: Storage, sample_news_items) -> None:
    store.upsert_news("genshin", sample_news_items)
    journal_mode = store.connect().execute("PRAGMA journal_mode").fetchone()[0]
    assert journal_mode.lower() == "wal"


def test_all_entities_roundtrip(store: Storage) -> None:
    store.upsert_posts([PostItem(post_id="p1", title="t", created_at="2024-01-01")])
    store.upsert_weibo([WeiboItem(post_id="w1", text="x", created_at="2024-01-01")])
    store.upsert_tutorial([TutorialItem(character_id="c1", name="n", lang="zh-cn")])
    store.upsert_images([ImageItem(character_id="c1", name="n", image_url="https://x/1.png")])

    assert store.query_posts()[0].post_id == "p1"
    assert store.query_weibo()[0].post_id == "w1"
    assert store.count_table("tutorial") == 1
    assert store.query_images()[0].image_url == "https://x/1.png"


def test_incremental_url_lookup(store: Storage, sample_news_items) -> None:
    store.upsert_news("genshin", sample_news_items)
    urls = store.get_existing_urls("genshin")
    assert "https://ys.mihoyo.com/main/news/detail/1001" in urls
    assert store.get_existing_urls("zzz") == set()


def test_count_and_clear(store: Storage, sample_news_items) -> None:
    store.upsert_news("genshin", sample_news_items)
    store.upsert_news(
        "zzz",
        [NewsItem(game="zzz", iInfoId=1, sTitle="z", url="https://zzz.mihoyo.com/news/1")],
    )
    assert store.count_all() == {"genshin": 2, "zzz": 1}
    assert store.clear("genshin") == 2
    assert store.count_all() == {"zzz": 1}
    assert store.clear() == 1
    assert store.count_news() == 0
