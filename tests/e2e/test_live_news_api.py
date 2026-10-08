"""端到端：真实米哈游 content_v2_user API 连通性测试。

默认跳过（需 ``MIHOYO_E2E=1``），避免在常规测试运行中真实联网。
"""

from __future__ import annotations

import os

import pytest

from mihoyo_toolkit.core.models import NewsItem
from mihoyo_toolkit.scrapers.api_client import MiHoYoApiClient

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("MIHOYO_E2E") != "1",
        reason="需 MIHOYO_E2E=1 才执行真实网络测试",
    ),
]


def test_live_genshin_news_api() -> None:
    client = MiHoYoApiClient("genshin", incremental=False)
    items = client.fetch_all()

    assert isinstance(items, list)
    assert items, "真实 API 应返回至少一条新闻"
    assert all(isinstance(item, NewsItem) for item in items)
    assert all(item.url.startswith("http") for item in items)


def test_live_genshin_first_page() -> None:
    client = MiHoYoApiClient("genshin", incremental=False)
    url = client.build_page_url(1)
    assert "getContentList" in url
