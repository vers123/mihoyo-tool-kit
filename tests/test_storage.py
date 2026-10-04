"""core.storage 单元测试

用临时 db 文件，避免污染真实 data/news.db。
覆盖建表、upsert 去重、existing 查询、count、表隔离、不支持游戏异常。
"""

import tempfile
import unittest
from pathlib import Path

from core.storage import NewsStorage


class TestNewsStorage(unittest.TestCase):
    def setUp(self):
        # 临时 db 文件，避免污染真实 data/news.db
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.store = NewsStorage(db_path=self._tmp.name)

    def tearDown(self):
        self.store.close()
        Path(self._tmp.name).unlink(missing_ok=True)

    def _item(self, info_id, title="T", url=None):
        return {
            "iInfoId": str(info_id),
            "sTitle": title,
            "date": "2024-01-01",
            "sCategoryName": "C",
            "sIntro": "I",
            "poster_url": "http://img/x.jpg",
            "url": url or f"http://example.com/{info_id}",
        }

    def test_upsert_new_items(self):
        n = self.store.upsert_items("genshin", [self._item(1), self._item(2)])
        self.assertEqual(n, 2)
        self.assertEqual(self.store.count("genshin"), 2)

    def test_upsert_dedup_ignores_existing(self):
        """INSERT OR IGNORE：重复 iInfoId 跳过"""
        self.store.upsert_items("genshin", [self._item(1)])
        n = self.store.upsert_items("genshin", [self._item(1), self._item(2)])
        self.assertEqual(n, 1)  # 仅新增 1 条
        self.assertEqual(self.store.count("genshin"), 2)

    def test_get_existing_urls(self):
        self.store.upsert_items("genshin", [self._item(1, url="http://x/1")])
        urls = self.store.get_existing_urls("genshin")
        self.assertIn("http://x/1", urls)

    def test_get_existing_ids(self):
        self.store.upsert_items("zzz", [self._item(10)])
        ids = self.store.get_existing_ids("zzz")
        self.assertIn("10", ids)

    def test_count_all(self):
        self.store.upsert_items("genshin", [self._item(1), self._item(2)])
        self.store.upsert_items("zzz", [self._item(3)])
        all_counts = self.store.count_all()
        self.assertEqual(all_counts["genshin"], 2)
        self.assertEqual(all_counts["zzz"], 1)
        self.assertEqual(all_counts["starrail"], 0)

    def test_tables_isolated(self):
        """同 iInfoId 在不同游戏表互不影响"""
        self.store.upsert_items("genshin", [self._item(1)])
        self.store.upsert_items("zzz", [self._item(1)])
        self.assertEqual(self.store.count("genshin"), 1)
        self.assertEqual(self.store.count("zzz"), 1)

    def test_unsupported_game_raises(self):
        with self.assertRaises(ValueError):
            self.store.upsert_items("unknown", [self._item(1)])
        with self.assertRaises(ValueError):
            self.store.count("unknown")

    def test_context_manager(self):
        with NewsStorage(db_path=self._tmp.name) as s:
            s.upsert_items("starrail", [self._item(1)])
            self.assertEqual(s.count("starrail"), 1)

    def test_init_creates_all_tables(self):
        """建表幂等：重复 init 不报错"""
        # 再开一次同一 db，schema 已存在应 IF NOT EXISTS 跳过
        s2 = NewsStorage(db_path=self._tmp.name)
        s2.upsert_items("starrail", [self._item(99)])
        self.assertEqual(s2.count("starrail"), 1)
        s2.close()


if __name__ == "__main__":
    unittest.main()
