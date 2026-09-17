"""
TxtFilter 单元测试
覆盖：行解析、关键词匹配、字段提取、多文件合并、日期降序排序、重编号、无日期文件处理
"""

import os
import tempfile
import unittest

from extractors.txt_filter import (
    TxtFilter,
    FIELD_ALL, FIELD_TITLE, FIELD_TITLE_INTRO, FIELD_TITLE_INTRO_CAT,
)


class TestParseLine(unittest.TestCase):
    """测试 parse_line 对四种格式的兼容"""

    def setUp(self):
        self.tf = TxtFilter()

    def test_parse_7field(self):
        line = "0001-活动标题-[2026-09-05 12:00:00]-[公告]-[摘要内容]-[https://img.jpg]-(https://ys.mihoyo.com/main/news/detail/1)"
        r = self.tf.parse_line(line)
        self.assertIsNotNone(r)
        self.assertEqual(r["index"], "0001")
        self.assertEqual(r["title"], "活动标题")
        self.assertEqual(r["date"], "2026-09-05 12:00:00")
        self.assertEqual(r["category"], "公告")
        self.assertEqual(r["intro"], "摘要内容")
        self.assertTrue(r["has_date"])

    def test_parse_4field(self):
        line = "0001-帖子标题-[2026-09-05]-(https://www.miyoushe.com/ys/article/1)"
        r = self.tf.parse_line(line)
        self.assertIsNotNone(r)
        self.assertEqual(r["index"], "0001")
        self.assertEqual(r["title"], "帖子标题")
        self.assertEqual(r["date"], "2026-09-05")
        self.assertTrue(r["has_date"])

    def test_parse_3field_characters(self):
        line = "0001-10000002-神里绫华"
        r = self.tf.parse_line(line)
        self.assertIsNotNone(r)
        self.assertEqual(r["index"], "0001")
        self.assertEqual(r["title"], "神里绫华")
        self.assertFalse(r["has_date"])

    def test_parse_2field_image_urls(self):
        line = "0001-旅行者·风-[https://act-upload.mihoyo.com/img.png]"
        r = self.tf.parse_line(line)
        self.assertIsNotNone(r)
        self.assertEqual(r["index"], "0001")
        self.assertEqual(r["title"], "旅行者·风")
        self.assertFalse(r["has_date"])

    def test_parse_empty_line(self):
        self.assertIsNone(self.tf.parse_line(""))
        self.assertIsNone(self.tf.parse_line("   \n"))


class TestMatchKeywords(unittest.TestCase):
    """测试 OR 逻辑匹配"""

    def test_single_keyword_match(self):
        self.assertTrue(TxtFilter.match_keywords("原神活动预告", ["原神"]))

    def test_single_keyword_no_match(self):
        self.assertFalse(TxtFilter.match_keywords("绝区零新闻", ["原神"]))

    def test_multi_keywords_any_match(self):
        """OR 逻辑：任一关键词命中即匹配"""
        self.assertTrue(TxtFilter.match_keywords("原神活动预告", ["原神", "祈愿"]))

    def test_multi_keywords_none_match(self):
        self.assertFalse(TxtFilter.match_keywords("绝区零新闻", ["原神", "祈愿"]))

    def test_case_insensitive_match(self):
        self.assertTrue(TxtFilter.match_keywords("Genshin Impact News", ["genshin"]))

    def test_case_insensitive_mixed(self):
        self.assertTrue(TxtFilter.match_keywords("Genshin 活动预告", ["GENSHIN", "活动"]))

    def test_case_insensitive_no_match(self):
        self.assertFalse(TxtFilter.match_keywords("原神新闻", ["ZZZ"]))


class TestExtractMatchText(unittest.TestCase):
    """测试不同字段选择下的匹配文本提取"""

    def setUp(self):
        self.tf = TxtFilter()
        self.parsed_7 = self.tf.parse_line(
            "0001-活动标题-[2026-09-05 12:00:00]-[公告]-[摘要内容]-[img.jpg]-(https://example.com/url)"
        )
        self.parsed_4 = self.tf.parse_line(
            "0001-帖子标题-[2026-09-05]-(https://example.com/url)"
        )

    def test_field_all_uses_raw(self):
        text = self.tf.extract_match_text(self.parsed_7, FIELD_ALL)
        self.assertEqual(text, self.parsed_7["raw"])

    def test_field_title_only(self):
        text = self.tf.extract_match_text(self.parsed_7, FIELD_TITLE)
        self.assertEqual(text, "活动标题")

    def test_field_title_intro(self):
        text = self.tf.extract_match_text(self.parsed_7, FIELD_TITLE_INTRO)
        self.assertIn("活动标题", text)
        self.assertIn("摘要内容", text)

    def test_field_title_intro_cat(self):
        text = self.tf.extract_match_text(self.parsed_7, FIELD_TITLE_INTRO_CAT)
        self.assertIn("活动标题", text)
        self.assertIn("摘要内容", text)
        self.assertIn("公告", text)

    def test_field_title_4field_no_intro(self):
        """4字段无摘要，FIELD_TITLE_INTRO 只返回标题"""
        text = self.tf.extract_match_text(self.parsed_4, FIELD_TITLE_INTRO)
        self.assertEqual(text.strip(), "帖子标题")


class TestFilterAndSort(unittest.TestCase):
    """测试过滤+排序+重编号的完整流程"""

    def setUp(self):
        self.tf = TxtFilter()
        self.tmpdir = tempfile.mkdtemp()

    def _write_tmp(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_filter_7field_by_title(self):
        content = (
            "0001-原神活动预告-[2026-09-01 12:00:00]-[公告]-[摘要]-[img]-(https://example.com/url1)\n"
            "0002-绝区零新闻-[2026-09-02 12:00:00]-[新闻]-[摘要]-[img]-(https://example.com/url2)\n"
            "0003-原神祈愿-[2026-09-03 12:00:00]-[祈愿]-[摘要]-[img]-(https://example.com/url3)\n"
        )
        path = self._write_tmp("test7.txt", content)
        items, nodate = self.tf.filter_and_sort(
            [path], ["原神"], FIELD_TITLE
        )
        self.assertEqual(len(items), 2)
        self.assertFalse(nodate)
        # 日期降序：0903 在前
        self.assertEqual(items[0]["date"], "2026-09-03 12:00:00")
        self.assertEqual(items[1]["date"], "2026-09-01 12:00:00")
        # 重编号 0001, 0002
        self.assertEqual(items[0]["index"], "0001")
        self.assertEqual(items[1]["index"], "0002")
        # raw 行首已更新
        self.assertTrue(items[0]["raw"].startswith("0001-"))
        self.assertTrue(items[1]["raw"].startswith("0002-"))

    def test_filter_multi_keywords_or(self):
        """OR 逻辑：包含任一关键词的行都匹配"""
        content = (
            "0001-原神活动祈愿-[2026-09-01]-[公告]-[摘要]-[img]-(https://example.com/url1)\n"
            "0002-原神活动预告-[2026-09-02]-[公告]-[摘要]-[img]-(https://example.com/url2)\n"
            "0003-绝区零活动祈愿-[2026-09-03]-[新闻]-[摘要]-[img]-(https://example.com/url3)\n"
        )
        path = self._write_tmp("test_or.txt", content)
        items, _ = self.tf.filter_and_sort(
            [path], ["原神", "祈愿"], FIELD_TITLE
        )
        # OR 逻辑：原神活动祈愿(含原神+祈愿)、原神活动预告(含原神)、绝区零活动祈愿(含祈愿)
        self.assertEqual(len(items), 3)
        # 按日期降序，最新的排前面
        self.assertEqual(items[0]["title"], "绝区零活动祈愿")
        self.assertEqual(items[1]["title"], "原神活动预告")
        self.assertEqual(items[2]["title"], "原神活动祈愿")

    def test_filter_4field_posts(self):
        content = (
            "0001-帖子A-[2026-09-01]-(https://example.com/url1)\n"
            "0002-帖子B-[2026-09-02]-(https://example.com/url2)\n"
        )
        path = self._write_tmp("test4.txt", content)
        items, _ = self.tf.filter_and_sort(
            [path], ["帖子"], FIELD_ALL
        )
        self.assertEqual(len(items), 2)
        # 日期降序
        self.assertEqual(items[0]["date"], "2026-09-02")
        self.assertEqual(items[1]["date"], "2026-09-01")

    def test_multi_file_merge(self):
        f1_content = "0001-原神A-[2026-09-01]-[公告]-[摘要]-[img]-(https://example.com/url1)\n"
        f2_content = "0002-原神B-[2026-09-05]-[公告]-[摘要]-[img]-(https://example.com/url2)\n"
        p1 = self._write_tmp("f1.txt", f1_content)
        p2 = self._write_tmp("f2.txt", f2_content)
        items, _ = self.tf.filter_and_sort(
            [p1, p2], ["原神"], FIELD_ALL
        )
        self.assertEqual(len(items), 2)
        # 0905 在前
        self.assertEqual(items[0]["date"], "2026-09-05")
        self.assertEqual(items[1]["date"], "2026-09-01")
        # 重编号连续
        self.assertEqual(items[0]["index"], "0001")
        self.assertEqual(items[1]["index"], "0002")

    def test_nodate_file_keeps_original_order(self):
        """无日期文件保持原顺序，排在末尾"""
        content = (
            "0001-10000001-角色A\n"
            "0002-10000002-角色B\n"
            "0003-10000003-角色C\n"
        )
        path = self._write_tmp("chars.txt", content)
        items, has_nodate = self.tf.filter_and_sort(
            [path], ["角色"], FIELD_ALL
        )
        self.assertEqual(len(items), 3)
        self.assertTrue(has_nodate)
        # 保持原顺序
        self.assertEqual(items[0]["title"], "角色A")
        self.assertEqual(items[2]["title"], "角色C")
        # 重编号
        self.assertEqual(items[0]["index"], "0001")

    def test_mixed_dated_nodate_single_keyword(self):
        """混合文件单关键词：有日期排前降序，无日期排后原顺序"""
        dated = "0001-活动A-[2026-09-01]-[公告]-[摘要]-[img]-(https://example.com/url1)\n"
        nodate = "0001-10000001-角色A\n0002-10000002-角色B\n"
        p1 = self._write_tmp("dated.txt", dated)
        p2 = self._write_tmp("nodate.txt", nodate)
        # 用 "A" 作为关键词，匹配标题含 A 的行
        items, has_nodate = self.tf.filter_and_sort(
            [p1, p2], ["A"], FIELD_TITLE
        )
        # dated 行标题 "活动A" 命中
        # nodate 行标题 "角色A" 和 "角色B"
        # FIELD_TITLE 对 3字段格式，title 是第3组=名称
        # "角色A" 匹配 A，"角色B" 不匹配
        self.assertEqual(len(items), 2)
        # 有日期排前
        self.assertTrue(items[0]["has_date"])
        self.assertFalse(items[1]["has_date"])
        self.assertTrue(has_nodate)
        # 重编号
        self.assertEqual(items[0]["index"], "0001")
        self.assertEqual(items[1]["index"], "0002")

    def test_no_match_returns_empty(self):
        content = "0001-原神活动-[2026-09-01]-[公告]-[摘要]-[img]-(https://example.com/url1)\n"
        path = self._write_tmp("nomatch.txt", content)
        items, _ = self.tf.filter_and_sort(
            [path], ["不存在的关键词"], FIELD_ALL
        )
        self.assertEqual(len(items), 0)


class TestOutputName(unittest.TestCase):
    """测试输出文件名生成"""

    def setUp(self):
        self.tf = TxtFilter()

    def test_single_file_name(self):
        paths = ["/tmp/data/results/news_genshin.txt"]
        name = self.tf.build_output_name(paths, ["原神", "活动"])
        self.assertEqual(name, "news_genshin_原神_活动.txt")

    def test_multi_file_name(self):
        paths = ["/tmp/f1.txt", "/tmp/f2.txt"]
        name = self.tf.build_output_name(paths, ["关键词"])
        self.assertEqual(name, "merged_关键词.txt")

    def test_unsafe_chars_sanitized(self):
        paths = ["/tmp/test.txt"]
        name = self.tf.build_output_name(paths, ["a/b", "c:d"])
        self.assertNotIn("/", name)
        self.assertNotIn(":", name)


if __name__ == "__main__":
    unittest.main()
