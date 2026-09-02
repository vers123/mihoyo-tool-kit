"""core.feed RSS/JSON Feed 单元测试"""

import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from core.feed import generate_json_feed, generate_rss_feed
from core.storage import NewsStorage


class TestFeed(unittest.TestCase):
    def setUp(self):
        self._db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db.close()
        self._rss = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
        self._rss.close()
        Path(self._rss.name).unlink()
        self._json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._json.close()
        Path(self._json.name).unlink()
        self.store = NewsStorage(db_path=self._db.name)

    def tearDown(self):
        self.store.close()
        Path(self._db.name).unlink(missing_ok=True)
        Path(self._rss.name).unlink(missing_ok=True)
        Path(self._json.name).unlink(missing_ok=True)

    def _item(self, info_id):
        return {
            "iInfoId": str(info_id),
            "sTitle": f"标题{info_id}",
            "date": "2024-01-01",
            "sCategoryName": "公告",
            "sIntro": "摘要",
            "poster_url": "http://img/x.jpg",
            "url": f"http://example.com/{info_id}",
        }

    def test_rss_valid_xml(self):
        self.store.upsert_items("genshin", [self._item(1)])
        out = generate_rss_feed(output_path=self._rss.name, db_path=self._db.name)
        tree = ET.parse(out)
        root = tree.getroot()
        self.assertEqual(root.tag, "rss")
        items = root.findall(".//item")
        self.assertEqual(len(items), 1)
        self.assertIn("标题1", items[0].find("title").text)
        self.assertIn("原神", items[0].find("category").text)

    def test_rss_multi_games(self):
        self.store.upsert_items("genshin", [self._item(1)])
        self.store.upsert_items("zzz", [self._item(2)])
        generate_rss_feed(output_path=self._rss.name, db_path=self._db.name)
        tree = ET.parse(self._rss.name)
        self.assertEqual(len(tree.findall(".//item")), 2)

    def test_json_valid_json(self):
        self.store.upsert_items("genshin", [self._item(1)])
        out = generate_json_feed(output_path=self._json.name, db_path=self._db.name)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], "https://jsonfeed.org/version/1.2")
        self.assertEqual(len(data["items"]), 1)
        self.assertIn("标题1", data["items"][0]["title"])

    def test_empty_db(self):
        """空库生成有效空 feed"""
        out = generate_rss_feed(output_path=self._rss.name, db_path=self._db.name)
        tree = ET.parse(out)
        self.assertEqual(len(tree.findall(".//item")), 0)

    def test_selective_games(self):
        self.store.upsert_items("genshin", [self._item(1)])
        self.store.upsert_items("zzz", [self._item(2)])
        generate_rss_feed(
            games=["genshin"], output_path=self._rss.name, db_path=self._db.name
        )
        tree = ET.parse(self._rss.name)
        self.assertEqual(len(tree.findall(".//item")), 1)

    def test_rss_guid_unique(self):
        """guid 应含 game+iInfoId 保证跨游戏唯一"""
        self.store.upsert_items("genshin", [self._item(1)])
        self.store.upsert_items("zzz", [self._item(1)])  # 同 id 不同游戏
        generate_rss_feed(output_path=self._rss.name, db_path=self._db.name)
        tree = ET.parse(self._rss.name)
        guids = [g.text for g in tree.findall(".//guid")]
        self.assertEqual(len(set(guids)), 2)


if __name__ == "__main__":
    unittest.main()
