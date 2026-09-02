"""O15 HAR fixture 测试

用样本 content_v2_user 响应（tests/fixtures/har/）验证 api_client._extract_items
的解析逻辑。API 字段变化时可用 fixture 回归测试，无需真实抓取。
"""

import json
import unittest
from pathlib import Path

from core.api_client import MiHoYoApiClient

FIXTURE = Path(__file__).parent / "fixtures" / "har" / "genshin_content_v2.json"


class TestHarFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as f:
            cls.response = json.load(f)
        cls.client = MiHoYoApiClient("genshin")

    def test_fixture_has_expected_structure(self):
        """fixture 应含 data.list 且非空"""
        self.assertIn("data", self.response)
        self.assertIn("list", self.response["data"])
        self.assertGreater(len(self.response["data"]["list"]), 0)

    def test_extract_items_parses_fixture(self):
        """_extract_items 应解析出 fixture 的两条新闻"""
        items = self.client._extract_items(self.response)
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertIn("iInfoId", item)
            self.assertIn("sTitle", item)
            self.assertIn("url", item)
            self.assertIn("date", item)
            self.assertIn("sCategoryName", item)

    def test_extract_items_fields_values(self):
        """字段值与 fixture 一致"""
        items = self.client._extract_items(self.response)
        self.assertEqual(items[0]["iInfoId"], "1001")
        self.assertEqual(items[0]["sTitle"], "测试新闻一")
        self.assertEqual(items[1]["sCategoryName"], "活动")

    def test_extract_items_empty_list(self):
        """空 list 返回空"""
        self.assertEqual(self.client._extract_items({"data": {"list": []}}), [])

    def test_extract_items_malformed(self):
        """畸形响应不崩，返回空"""
        self.assertEqual(self.client._extract_items(None), [])
        self.assertEqual(self.client._extract_items({}), [])
        self.assertEqual(
            self.client._extract_items({"data": {}}), []
        )

    def test_extract_items_skips_missing_id_or_title(self):
        """缺 iInfoId 或 sTitle 的条目应被跳过"""
        resp = {
            "data": {
                "list": [
                    {"iInfoId": 1, "sTitle": ""},  # 空 title 跳过
                    {"sTitle": "T"},  # 缺 id 跳过
                    {"iInfoId": 3, "sTitle": "OK"},
                ]
            }
        }
        items = self.client._extract_items(resp)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["iInfoId"], "3")


if __name__ == "__main__":
    unittest.main()
