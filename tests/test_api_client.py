"""core.api_client 单元测试

覆盖纯逻辑（URL 构造、响应解析、封面提取、URL 拼接）与抓取流程
（mock httpx，验证分页收敛与增量停止），不发真实网络请求。
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from core.api_client import MiHoYoApiClient


def _mock_response(data: dict) -> MagicMock:
    """构造 httpx.Response mock"""
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


class TestUrlBuilding(unittest.TestCase):
    """URL 构造与拼接"""

    def setUp(self):
        self.client = MiHoYoApiClient("genshin")

    def test_build_page_url_contains_all_params(self):
        url = self.client._build_page_url(1)
        self.assertIn("iPage=1", url)
        self.assertIn("iPageSize=5", url)  # 原神 page_size=5
        self.assertIn("iChanId=719", url)  # 原神 chan_id=719
        self.assertIn("sLangKey=zh-cn", url)

    def test_build_page_url_increments_page(self):
        self.assertIn("iPage=3", self.client._build_page_url(3))

    def test_make_full_url_relative(self):
        full = self.client._make_full_url("/main/news/detail/123")
        self.assertEqual(full, "https://ys.mihoyo.com/main/news/detail/123")

    def test_make_full_url_already_absolute(self):
        abs_url = "https://example.com/x"
        self.assertEqual(self.client._make_full_url(abs_url), abs_url)


class TestExtractItems(unittest.TestCase):
    """content_v2_user 响应解析"""

    def setUp(self):
        self.client = MiHoYoApiClient("genshin")

    def _make_item(self, info_id, title, poster_url=None):
        s_ext = json.dumps({"720_1": [{"url": poster_url}]}) if poster_url else ""
        return {
            "iInfoId": info_id,
            "sTitle": title,
            "dtStartTime": "2024-01-01",
            "sCategoryName": "公告",
            "sIntro": "摘要",
            "sExt": s_ext,
        }

    def test_extract_items_fields(self):
        data = {"data": {"list": [self._make_item(123, "标题1", "http://img/1.jpg")]}}
        items = self.client._extract_items(data)
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["iInfoId"], "123")
        self.assertEqual(it["sTitle"], "标题1")
        self.assertEqual(it["sCategoryName"], "公告")
        self.assertEqual(it["sIntro"], "摘要")
        self.assertEqual(it["poster_url"], "http://img/1.jpg")
        self.assertEqual(it["url"], "https://ys.mihoyo.com/main/news/detail/123")

    def test_extract_items_skips_invalid(self):
        # 缺 iInfoId 或 sTitle 应被跳过
        data = {"data": {"list": [
            {"iInfoId": "", "sTitle": "x"},
            {"iInfoId": "1", "sTitle": ""},
            self._make_item(1, "ok"),
        ]}}
        items = self.client._extract_items(data)
        self.assertEqual(len(items), 1)

    def test_extract_items_empty_data(self):
        self.assertEqual(self.client._extract_items({}), [])
        self.assertEqual(self.client._extract_items({"data": {}}), [])
        self.assertEqual(self.client._extract_items({"data": {"list": "not-list"}}), [])

    def test_extract_poster_url_from_list(self):
        item = {"sExt": json.dumps({"720_1": [{"url": "http://img/x.jpg"}]})}
        self.assertEqual(self.client._extract_poster_url(item), "http://img/x.jpg")

    def test_extract_poster_url_from_dict(self):
        item = {"sExt": json.dumps({"720_1": {"url": "http://img/y.jpg"}})}
        self.assertEqual(self.client._extract_poster_url(item), "http://img/y.jpg")

    def test_extract_poster_url_missing(self):
        self.assertEqual(self.client._extract_poster_url({}), "")
        self.assertEqual(self.client._extract_poster_url({"sExt": "bad-json"}), "")


class TestFetchAll(unittest.TestCase):
    """抓取主流程（mock httpx）"""

    def _page(self, items, iTotal=None):
        return {"data": {"iTotal": iTotal if iTotal is not None else len(items), "list": items}}

    @patch("core.api_client.httpx.Client")
    def test_fetch_all_stops_at_last_page(self, MockClient):
        # 原神 page_size=5，返回 2 条 (<5) 即视为最后一页
        client_inst = MagicMock()
        MockClient.return_value.__enter__.return_value = client_inst
        client_inst.get.return_value = _mock_response(
            self._page([{"iInfoId": 1, "sTitle": "a"}, {"iInfoId": 2, "sTitle": "b"}], iTotal=2)
        )

        c = MiHoYoApiClient("genshin")
        items = c.fetch_all()
        self.assertEqual(len(items), 2)
        # 只请求了一页
        self.assertEqual(client_inst.get.call_count, 1)

    @patch("core.api_client.httpx.Client")
    def test_fetch_all_incremental_stops_on_existing(self, MockClient):
        client_inst = MagicMock()
        MockClient.return_value.__enter__.return_value = client_inst
        # 第一页返回 5 条（满页，本应继续），但其中一条 url 已存在 → 增量停止
        page_items = [{"iInfoId": i, "sTitle": f"t{i}"} for i in range(1, 6)]
        client_inst.get.return_value = _mock_response(self._page(page_items, iTotal=100))

        # 预置已存在 url（detail/1）
        existing = {"https://ys.mihoyo.com/main/news/detail/1"}
        c = MiHoYoApiClient("genshin", incremental=True, existing_urls=existing)
        items = c.fetch_all()
        # 增量模式下收集到本页后即停止（5 条）
        self.assertEqual(len(items), 5)
        # 因为命中已存在，没有继续请求第二页
        self.assertEqual(client_inst.get.call_count, 1)

    @patch("core.api_client.httpx.Client")
    def test_fetch_all_empty_response_returns_empty(self, MockClient):
        client_inst = MagicMock()
        MockClient.return_value.__enter__.return_value = client_inst
        client_inst.get.return_value = _mock_response({"data": {"list": []}})

        c = MiHoYoApiClient("genshin")
        self.assertEqual(c.fetch_all(), [])


if __name__ == "__main__":
    unittest.main()
