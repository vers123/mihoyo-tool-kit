"""其余抓取器（user / weibo / baike / tutorial / custom）单元测试。"""

from __future__ import annotations

from pathlib import Path

import mihoyo_toolkit.scrapers.baike as baike_module
import mihoyo_toolkit.scrapers.custom as custom_module
import mihoyo_toolkit.scrapers.tutorial as tutorial_module
import mihoyo_toolkit.scrapers.user as user_module
import mihoyo_toolkit.scrapers.weibo as weibo_module
from mihoyo_toolkit.core.models import PostItem
from mihoyo_toolkit.core.paths import get_path_manager
from mihoyo_toolkit.scrapers.baike import BaikeScraper, run_baike
from mihoyo_toolkit.scrapers.custom import CustomScraper, run_custom
from mihoyo_toolkit.scrapers.tutorial import (
    TutorialScraper,
    _extract_all_links,
    _extract_characters,
    _is_changelog,
    run_tutorial,
    run_tutorial_batch,
)
from mihoyo_toolkit.scrapers.user import UserScraper, run_user
from mihoyo_toolkit.scrapers.weibo import WeiboScraper, run_weibo

BAIKE_HTML = (
    '<div class="collection-avatar__item">'
    '<img data-src="https://webstatic.mihoyo.com/upload/a.png?x-oss-process=1" />'
    '<div class="collection-avatar__title">角色A</div></div>'
    '<div class="collection-avatar__item">'
    '<img data-src="https://webstatic.mihoyo.com/upload/b.png?x" />'
    '<div class="collection-avatar__title">角色B</div></div>'
)

TUTORIAL_HTML = (
    '<tr class="table-row"><td><p><span>10000001</span></p></td>'
    "<td><p><span>角色A</span></p></td></tr>"
)

INDEX_HTML = (
    "<h1>更新日志</h1>"
    '<a href="https://act.mihoyo.com/ys/ugc/tutorial/detail/abc123">教程一</a>'
    '<a href="https://act.mihoyo.com/ys/ugc/tutorial/detail/def456">教程二</a>'
)


# ====================================================================== #
#  用户发帖
# ====================================================================== #
def test_user_scraper_metadata() -> None:
    scraper = UserScraper(incremental=False)
    assert scraper.name == "user"
    assert scraper.config.output_filename == "user_posts.html"
    assert scraper.config.scraper_name == "user"


def test_user_extract_items_from_api() -> None:
    scraper = UserScraper(incremental=False)
    data = {
        "data": {
            "list": [
                {
                    "post": {
                        "post_id": "1",
                        "subject": "标题",
                        "created_at": 1700000000,
                        "content": "c",
                    }
                },
                {"post": {"post_id": "2", "created_at": "2024-01-02"}},
                {"post": {"post_id": ""}},
                {"post_id": "3"},
                "not-a-dict",
            ]
        }
    }
    items = scraper.extract_items_from_api(data)
    assert [item.post_id for item in items] == ["1", "2", "3"]
    assert items[0].created_at.count("-") == 2  # 时间戳转日期字符串

    assert scraper.extract_items_from_api("bad") == []
    assert scraper.extract_items_from_api({"data": {"list": "bad"}}) == []


def test_user_fetch_uses_api_items(monkeypatch) -> None:
    scraper = UserScraper(incremental=False)

    def fake_run(**_kwargs) -> str:
        scraper._api_items = [PostItem(post_id="1")]
        return "<html>"

    monkeypatch.setattr(scraper, "run", fake_run)
    assert [item.post_id for item in scraper.fetch()] == ["1"]


def test_user_fetch_from_har(monkeypatch) -> None:
    scraper = UserScraper(incremental=False)
    monkeypatch.setattr(
        user_module,
        "load_har_entries",
        lambda name: [{"data": {"list": [{"post": {"post_id": "9"}}]}}],
    )
    assert [item.post_id for item in scraper._fetch_from_har()] == ["9"]


def test_user_fetch_falls_back_to_har(monkeypatch) -> None:
    scraper = UserScraper(incremental=False)
    monkeypatch.setattr(scraper, "run", lambda **_kwargs: "<html>")
    monkeypatch.setattr(scraper, "check_api_or_har", lambda: "use_har")
    monkeypatch.setattr(
        user_module,
        "load_har_entries",
        lambda name: [{"data": {"list": [{"post": {"post_id": "9"}}]}}],
    )
    assert [item.post_id for item in scraper.fetch()] == ["9"]


def test_user_fetch_and_store(store, monkeypatch) -> None:
    scraper = UserScraper(incremental=False)
    monkeypatch.setattr(scraper, "fetch", lambda: [PostItem(post_id="p1", title="t")])
    assert scraper.fetch_and_store() == 1

    empty = UserScraper(incremental=False)
    monkeypatch.setattr(empty, "fetch", lambda: [])
    assert empty.fetch_and_store() == 0


def test_user_incremental_loads_existing(store) -> None:
    store.upsert_posts([PostItem(post_id="p1", url="https://www.miyoushe.com/ys/article/p1")])
    scraper = UserScraper(incremental=True)
    assert scraper.config.existing_urls == {"https://www.miyoushe.com/ys/article/p1"}


def test_run_user(monkeypatch) -> None:
    monkeypatch.setattr(UserScraper, "fetch_and_store", lambda self: 5)
    assert run_user(incremental=False) == 5


# ====================================================================== #
#  微博
# ====================================================================== #
class _FakeCtx:
    def __init__(self, cookies=None) -> None:
        self._cookies = cookies or []

    def cookies(self):
        return self._cookies


class _FakeResp:
    def __init__(self, payload, ok: bool = True, status: int = 200) -> None:
        self._payload = payload
        self.ok = ok
        self.status = status

    def json(self):
        return self._payload


class _FakeRequest:
    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, headers=None):
        response = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return response


class _FakePage:
    def __init__(self, responses=(), cookies=None) -> None:
        self.request = _FakeRequest(responses)
        self.context = _FakeCtx(cookies)


class _FakeSession:
    def __init__(self, page) -> None:
        self.page = page


def test_weibo_metadata_and_user_id() -> None:
    scraper = WeiboScraper(incremental=False)
    assert scraper.name == "weibo"
    assert scraper.user_id == "6593199887"
    assert WeiboScraper._extract_user_id("https://weibo.com/u/12345") == "12345"
    assert WeiboScraper._extract_user_id("https://weibo.com/none") == "6593199887"


def test_weibo_extract_items_from_api() -> None:
    scraper = WeiboScraper(incremental=False)
    data = {
        "data": {
            "list": [
                {"mblogid": "m1", "text_raw": "<b>hi</b>", "created_at": "x", "reposts_count": 1},
                {"bid": "b1"},
                {"mid": "mid1"},
                {"idstr": "i1"},
                {},
                "bad",
            ]
        }
    }
    items = scraper.extract_items_from_api(data)
    assert [item.post_id for item in items] == ["m1", "b1", "mid1", "i1"]
    assert items[0].text == "hi"
    assert items[0].url == "https://weibo.com/6593199887/m1"

    assert scraper.extract_items_from_api("bad") == []
    assert scraper.extract_items_from_api({"data": "bad"}) == []
    assert scraper.extract_items_from_api({"data": {"list": "bad"}}) == []


def test_weibo_needs_login() -> None:
    class LocPage:
        def __init__(self, count: int) -> None:
            self._count = count

        def locator(self, selector: str):
            return self

        def count(self) -> int:
            return self._count

    assert WeiboScraper._needs_login(LocPage(0)) is True
    assert WeiboScraper._needs_login(LocPage(3)) is False

    class BadPage:
        def locator(self, selector: str):
            raise RuntimeError("no page")

    assert WeiboScraper._needs_login(BadPage()) is True


def test_weibo_xsrf_token() -> None:
    scraper = WeiboScraper(incremental=False)
    page = _FakePage(cookies=[{"name": "XSRF-TOKEN", "value": "tok"}])
    assert scraper._get_xsrf_token(page) == "tok"
    assert scraper._get_xsrf_token(_FakePage(cookies=[])) == ""

    class BadCtx:
        def cookies(self):
            raise RuntimeError("bad")

    class BadPage:
        context = BadCtx()

    assert scraper._get_xsrf_token(BadPage()) == ""


def test_weibo_wait_for_login_returns_when_logged_in(monkeypatch) -> None:
    scraper = WeiboScraper(incremental=False)
    monkeypatch.setattr(scraper, "_needs_login", lambda page: False)
    scraper._wait_for_login(_FakePage())  # 直接返回


def test_weibo_wait_for_login_success_after_prompt(monkeypatch, capsys) -> None:
    scraper = WeiboScraper(incremental=False)
    calls = {"n": 0}

    def fake_needs_login(page) -> bool:
        calls["n"] += 1
        return calls["n"] == 1  # 首次需要登录，随后成功

    monkeypatch.setattr(scraper, "_needs_login", fake_needs_login)
    scraper._wait_for_login(_FakePage())
    assert "需要手动登录" in capsys.readouterr().out


def test_weibo_fetch_posts_via_api(monkeypatch) -> None:
    scraper = WeiboScraper(incremental=False)
    pages = [
        _FakeResp({"data": {"total": 2, "list": [{"mblogid": "m1"}], "since_id": "s1"}}),
        _FakeResp({"data": {"list": [{"mblogid": "m2"}], "since_id": ""}}),
    ]
    items = scraper._fetch_posts_via_api(_FakeSession(_FakePage(pages)))
    assert [item.post_id for item in items] == ["m1", "m2"]


def test_weibo_fetch_posts_via_api_empty_page() -> None:
    scraper = WeiboScraper(incremental=False)
    pages = [_FakeResp({"data": {"list": []}})]
    assert scraper._fetch_posts_via_api(_FakeSession(_FakePage(pages))) == []


def test_weibo_fetch_posts_via_api_http_error() -> None:
    scraper = WeiboScraper(incremental=False)
    pages = [_FakeResp({"data": {}}, ok=False, status=403)]
    assert scraper._fetch_posts_via_api(_FakeSession(_FakePage(pages))) == []


def test_weibo_fetch_posts_via_api_request_exception() -> None:
    scraper = WeiboScraper(incremental=False)

    class BadPage(_FakePage):
        def __init__(self) -> None:
            super().__init__([])
            self.request = self

        def get(self, url, headers=None):
            raise RuntimeError("network down")

    assert scraper._fetch_posts_via_api(_FakeSession(BadPage())) == []


def test_weibo_fetch_posts_via_api_incremental_stop() -> None:
    scraper = WeiboScraper(incremental=False)
    scraper.config.incremental_mode = True
    scraper.config.existing_urls = {"https://weibo.com/6593199887/m1"}
    pages = [_FakeResp({"data": {"total": 5, "list": [{"mblogid": "m1"}], "since_id": "s1"}})]
    items = scraper._fetch_posts_via_api(_FakeSession(_FakePage(pages)))
    assert [item.post_id for item in items] == ["m1"]


def test_weibo_fetch_and_store(store, monkeypatch) -> None:
    scraper = WeiboScraper(incremental=False)
    from mihoyo_toolkit.core.models import WeiboItem

    monkeypatch.setattr(scraper, "fetch", lambda: [WeiboItem(post_id="w1")])
    assert scraper.fetch_and_store() == 1


def _fake_browser_session_class(page, events=None):
    class FakeBrowserSession:
        def __init__(self, config) -> None:
            self.page = page
            if events is not None:
                events.append(config.headless)

        def start(self):
            return self

        def goto(self, url=None) -> None:
            pass

        def content(self) -> str:
            return "<html>weibo</html>"

        def stop(self) -> None:
            pass

    return FakeBrowserSession


def test_weibo_fetch_uses_ajax(monkeypatch, tmp_home: Path) -> None:
    scraper = WeiboScraper(incremental=False)
    payload = {"data": {"total": 1, "list": [{"mblogid": "m1"}], "since_id": ""}}
    page = _FakePage([_FakeResp(payload)])

    monkeypatch.setattr(weibo_module, "BrowserSession", _fake_browser_session_class(page))
    monkeypatch.setattr(scraper, "_needs_login", lambda page: False)
    monkeypatch.setattr(scraper, "_wait_for_login", lambda page: None)

    assert [item.post_id for item in scraper.fetch()] == ["m1"]


def test_weibo_fetch_switches_to_visible_browser(monkeypatch, tmp_home: Path) -> None:
    scraper = WeiboScraper(incremental=False)
    payload = {"data": {"total": 1, "list": [{"mblogid": "m1"}], "since_id": ""}}
    page = _FakePage([_FakeResp(payload)])
    events: list[bool] = []

    monkeypatch.setattr(weibo_module, "BrowserSession", _fake_browser_session_class(page, events))
    calls = {"n": 0}

    def fake_needs_login(page) -> bool:
        calls["n"] += 1
        return calls["n"] == 1

    monkeypatch.setattr(scraper, "_needs_login", fake_needs_login)
    monkeypatch.setattr(scraper, "_wait_for_login", lambda page: None)

    assert len(scraper.fetch()) == 1
    assert scraper.config.headless is False
    assert events == [True, False]


def test_weibo_fetch_no_data(monkeypatch, tmp_home: Path) -> None:
    scraper = WeiboScraper(incremental=False)
    page = _FakePage([_FakeResp({"data": {"list": []}})])

    monkeypatch.setattr(weibo_module, "BrowserSession", _fake_browser_session_class(page))
    monkeypatch.setattr(scraper, "_needs_login", lambda page: False)
    monkeypatch.setattr(scraper, "_wait_for_login", lambda page: None)

    assert scraper.fetch() == []


def test_weibo_fetch_from_har(monkeypatch) -> None:
    scraper = WeiboScraper(incremental=False)
    monkeypatch.setattr(
        weibo_module,
        "load_har_entries",
        lambda name: [{"data": {"list": [{"mblogid": "h1"}]}}],
    )
    assert [item.post_id for item in scraper._fetch_from_har()] == ["h1"]


def test_run_weibo(monkeypatch) -> None:
    monkeypatch.setattr(WeiboScraper, "fetch_and_store", lambda self: 4)
    assert run_weibo(incremental=False) == 4


# ====================================================================== #
#  角色图鉴
# ====================================================================== #
def test_baike_parse() -> None:
    scraper = BaikeScraper()
    assert scraper.name == "baike"
    assert scraper.extract_items_from_api({}) == []

    items = scraper.parse(BAIKE_HTML)
    # parse 会对结果做 reverse
    assert [item.name for item in items] == ["角色B", "角色A"]
    assert items[0].image_url == "https://webstatic.mihoyo.com/upload/b.png"


def test_run_baike(monkeypatch, store) -> None:
    monkeypatch.setattr(baike_module.BaikeScraper, "run", lambda self, **_kwargs: BAIKE_HTML)
    assert run_baike() == 2


def test_run_baike_no_items(monkeypatch) -> None:
    monkeypatch.setattr(baike_module.BaikeScraper, "run", lambda self, **_kwargs: "<html></html>")
    assert run_baike() == 0


# ====================================================================== #
#  教程
# ====================================================================== #
def test_tutorial_helpers() -> None:
    assert _extract_characters(TUTORIAL_HTML) == [("10000001", "角色A")]
    assert _extract_characters("<td><p>10000002</p></td><td><p>角色B</p></td>") == [
        ("10000002", "角色B")
    ]
    assert _is_changelog("更新日志") is True
    assert _is_changelog("7.0版本") is True
    assert _is_changelog("普通页面") is False
    assert _is_changelog("") is False

    links = _extract_all_links(
        '<a href="https://act.mihoyo.com/ys/ugc/tutorial//detail/abc123">标题</a>', "index"
    )
    assert links == [
        {
            "title": "标题",
            "url": "https://act.mihoyo.com/ys/ugc/tutorial/detail/abc123",
            "tutorial_id": "abc123",
        }
    ]
    assert _extract_all_links(links[0]["url"], "abc123") == []


def test_tutorial_scraper_metadata() -> None:
    with_lang = TutorialScraper("tid", "zh-cn")
    assert with_lang.name == "tutorial/zh-cn"
    assert with_lang.config.output_filename == "tutorial_tid_zh-cn.html"
    assert with_lang.extract_items_from_api({}) == []
    items = with_lang.parse(TUTORIAL_HTML)
    assert items[0].lang == "zh-cn"

    without_lang = TutorialScraper("tid")
    assert without_lang.name == "tutorial/default"
    assert without_lang.config.output_filename == "tutorial_tid_default.html"


def test_run_tutorial(monkeypatch, store) -> None:
    monkeypatch.setattr(
        tutorial_module.TutorialScraper, "run", lambda self, **_kwargs: TUTORIAL_HTML
    )
    run_tutorial("tid")
    assert store.count_table("tutorial") == 1


def test_run_tutorial_no_characters(monkeypatch) -> None:
    monkeypatch.setattr(
        tutorial_module.TutorialScraper, "run", lambda self, **_kwargs: "<html></html>"
    )
    run_tutorial("")  # 使用默认 id，未解析到角色


def test_run_tutorial_batch(monkeypatch, store) -> None:
    def fake_run(self, **_kwargs) -> str:
        return INDEX_HTML if self.tutorial_id == "index" else TUTORIAL_HTML

    monkeypatch.setattr(tutorial_module.TutorialScraper, "run", fake_run)

    assert run_tutorial_batch("index") == 2
    # 两个教程页解析出同一角色，按 (character_id, lang) 去重后仅 1 行
    assert store.count_table("tutorial") == 1


def test_run_tutorial_batch_skips_existing(monkeypatch, store, tmp_home: Path) -> None:
    html_dir = get_path_manager().html / "tutorial"
    html_dir.mkdir(parents=True, exist_ok=True)
    (html_dir / "tutorial_abc123_default.html").write_text("exists", encoding="utf-8")

    def fake_run(self, **_kwargs) -> str:
        return INDEX_HTML if self.tutorial_id == "index" else TUTORIAL_HTML

    monkeypatch.setattr(tutorial_module.TutorialScraper, "run", fake_run)

    assert run_tutorial_batch("index") == 1


def test_run_tutorial_batch_not_changelog(monkeypatch) -> None:
    monkeypatch.setattr(tutorial_module.TutorialScraper, "run", lambda self, **_kwargs: "<html/>")
    assert run_tutorial_batch("index") == 0


def test_run_tutorial_batch_no_links(monkeypatch) -> None:
    monkeypatch.setattr(
        tutorial_module.TutorialScraper, "run", lambda self, **_kwargs: "<h1>更新日志</h1>"
    )
    assert run_tutorial_batch("index") == 0


# ====================================================================== #
#  自定义页面
# ====================================================================== #
def test_custom_scraper() -> None:
    scraper = CustomScraper("https://example.com", "out.html")
    assert scraper.name == "custom"
    assert scraper.extract_items_from_api({}) == []


def test_run_custom(monkeypatch) -> None:
    monkeypatch.setattr(custom_module.CustomScraper, "run", lambda self, **_kwargs: "<html>")
    run_custom("https://example.com")  # 不抛异常


def test_run_custom_empty_url() -> None:
    run_custom("")  # 记录错误后返回
