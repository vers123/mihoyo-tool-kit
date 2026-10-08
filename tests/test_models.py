"""core.models NewsItem 单元测试"""

import unittest

from pydantic import ValidationError

from core.models import NewsItem


class TestNewsItem(unittest.TestCase):
    def test_valid_full_fields(self):
        item = NewsItem.model_validate(
            {
                "iInfoId": "123",
                "sTitle": "T",
                "date": "2024-01-01",
                "sCategoryName": "C",
                "sIntro": "I",
                "poster_url": "u",
                "url": "l",
            }
        )
        self.assertEqual(item.iInfoId, "123")
        self.assertEqual(item.sTitle, "T")
        self.assertEqual(item.poster_url, "u")

    def test_required_fields_missing_raises(self):
        with self.assertRaises(ValidationError):
            NewsItem.model_validate({"sTitle": "T"})  # 缺 iInfoId
        with self.assertRaises(ValidationError):
            NewsItem.model_validate({"iInfoId": "1"})  # 缺 sTitle

    def test_optional_fields_default_empty(self):
        item = NewsItem(iInfoId="1", sTitle="T")
        self.assertEqual(item.date, "")
        self.assertEqual(item.url, "")
        self.assertEqual(item.sIntro, "")

    def test_extra_fields_ignored(self):
        """extra='ignore'：响应多余字段不报错"""
        item = NewsItem.model_validate(
            {"iInfoId": "1", "sTitle": "T", "extra_field": "ignored"}
        )
        self.assertEqual(item.iInfoId, "1")

    def test_model_dump_returns_dict(self):
        """api_client 依赖 model_dump() 返回 dict 给 storage/excel"""
        item = NewsItem(iInfoId="1", sTitle="T")
        d = item.model_dump()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["iInfoId"], "1")
        self.assertEqual(d["sTitle"], "T")

    def test_int_input_raises(self):
        """Pydantic v2 默认不强转 int→str，int 输入验证失败
        （api_client 已用 str() 转换，故实际不会传 int 给 NewsItem）
        """
        with self.assertRaises(ValidationError):
            NewsItem.model_validate({"iInfoId": 123, "sTitle": "T", "date": 20240101})


if __name__ == "__main__":
    unittest.main()
