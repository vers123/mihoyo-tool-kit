"""端到端：真实米哈游 content_v2_user API 连通性测试。

默认跳过（需 ``MIHOYO_E2E=1``），避免在常规测试运行中真实联网。

用例按「请求次数」分两档：

* 默认：把 ``api_page_size`` 调大，使 ``fetch_all()`` 的 ``max_pages`` 收敛为 1
  —— **一次请求**走完整条 :meth:`MiHoYoApiClient.fetch_all` 路径（重试包装、
  ``iTotal`` 处理、解析、循环退出），秒级完成；
* ``MIHOYO_E2E_FULL=1``：真的走多页分页（``api_page_size`` 取 API 实际上限 300，
  原神约 4700 条 ≈ 16 页），验证跨页累加。
"""

from __future__ import annotations

import os

import pytest

from mihoyo_toolkit.core import get_settings
from mihoyo_toolkit.core.models import NewsItem
from mihoyo_toolkit.scrapers.api_client import MiHoYoApiClient

#: 让 fetch_all() 只发一次请求：API 会把 iPageSize 静默截断到 300，
#: 而 max_pages = ceil(iTotal / api_page_size) 随之收敛为 1。
SINGLE_REQUEST_PAGE_SIZE = 10_000

#: 完整分页模式下的每页条数（实测 API 上限为 300，用它把页数从上千压到十几页）
FULL_PAGINATION_PAGE_SIZE = 300

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("MIHOYO_E2E") != "1",
        reason="需 MIHOYO_E2E=1 才执行真实网络测试",
    ),
]


def _genshin_client(page_size: int) -> MiHoYoApiClient:
    """构造原神客户端，并覆盖站点配置里的每页条数（不修改全局配置）。"""
    site = get_settings().sources.news.get_site("genshin")
    return MiHoYoApiClient(
        "genshin",
        incremental=False,
        site=site.model_copy(update={"api_page_size": page_size}),
    )


def _assert_news_items(items: list[NewsItem]) -> None:
    """公共断言：返回真实 NewsItem 且链接、标题完整。"""
    assert isinstance(items, list)
    assert items, "真实 API 应返回至少一条新闻"
    assert all(isinstance(item, NewsItem) for item in items)
    assert all(item.url.startswith("http") for item in items)
    assert all(item.sTitle for item in items)


def test_live_genshin_news_api() -> None:
    """一次请求走完 fetch_all()（默认档，秒级）。"""
    _assert_news_items(_genshin_client(SINGLE_REQUEST_PAGE_SIZE).fetch_all())


def test_live_genshin_first_page() -> None:
    """分页 URL 构造正确（不发请求）。"""
    client = MiHoYoApiClient("genshin", incremental=False)
    url = client.build_page_url(1)
    assert "getContentList" in url


@pytest.mark.skipif(
    os.environ.get("MIHOYO_E2E_FULL") != "1",
    reason="完整分页抓取较慢，需 MIHOYO_E2E_FULL=1",
)
def test_live_genshin_full_pagination() -> None:
    """真实多页分页抓取（验证跨页累加，约十几页）。"""
    items = _genshin_client(FULL_PAGINATION_PAGE_SIZE).fetch_all()

    _assert_news_items(items)
    assert len(items) > FULL_PAGINATION_PAGE_SIZE, "完整分页应跨越多页累加"
