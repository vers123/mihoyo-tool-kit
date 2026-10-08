"""scrapers.browser 单元测试（Playwright 以假对象替换）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mihoyo_toolkit.core.exceptions import ScraperError
from mihoyo_toolkit.scrapers.browser import DEFAULT_BROWSER_ARGS, BrowserSession, open_browser
from mihoyo_toolkit.scrapers.config import ScrapeConfig


def _config(**overrides) -> ScrapeConfig:
    return ScrapeConfig.from_settings("https://example.com", "page.html", **overrides)


class _FakeLocator:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self) -> int:
        return self._count


class _FakeContext:
    def __init__(self) -> None:
        self.added_cookies: list[list[dict]] = []

    def new_page(self) -> _FakePage:
        return _FakePage()

    def add_cookies(self, cookies) -> None:
        self.added_cookies.append(list(cookies))


class _FakePage:
    def __init__(self, heights: list[int] | None = None) -> None:
        self.heights = list(heights or [1000])
        self.goto_url: str | None = None
        self.waited = False
        self.scrolled = 0

    def goto(self, url: str, timeout: int | None = None) -> None:
        self.goto_url = url

    def wait_for_load_state(self, state: str) -> None:
        self.waited = True

    def content(self) -> str:
        return "<html>content</html>"

    def evaluate(self, script: str, *args):
        if script == "document.body.scrollHeight":
            return self.heights.pop(0) if self.heights else 1000
        if script.startswith("window.scrollTo"):
            self.scrolled += 1
            return None
        return ["https://example.com/link"]


class _FakeBrowser:
    def __init__(self) -> None:
        self.context = _FakeContext()
        self.closed = False
        self.new_context_kwargs: dict | None = None

    def new_context(self, **kwargs) -> _FakeContext:
        self.new_context_kwargs = kwargs
        return self.context

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self) -> None:
        self.browser = _FakeBrowser()
        self.launch_kwargs: dict | None = None

    def launch(self, **kwargs) -> _FakeBrowser:
        self.launch_kwargs = kwargs
        return self.browser


class _FakePlaywright:
    def __init__(self) -> None:
        self.chromium = _FakeChromium()
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _FakeSyncPlaywright:
    def __init__(self) -> None:
        self.pw = _FakePlaywright()

    def start(self) -> _FakePlaywright:
        return self.pw


def test_page_and_browser_require_start() -> None:
    session = BrowserSession(_config())
    with pytest.raises(ScraperError):
        _ = session.page
    with pytest.raises(ScraperError):
        _ = session.browser


def test_page_and_browser_after_assignment() -> None:
    session = BrowserSession(_config())
    page = _FakePage()
    browser = _FakeBrowser()
    session._page = page
    session._browser = browser
    assert session.page is page
    assert session.browser is browser


def test_stop_without_start_is_noop() -> None:
    BrowserSession(_config()).stop()


def test_start_and_stop(monkeypatch) -> None:
    fake = _FakeSyncPlaywright()
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake)

    config = _config(
        headless=False,
        browser_args=[],
        use_firefox_cookies=True,
        api_domain_filter="weibo.com",
    )
    session = BrowserSession(config).start()

    assert session.page is not None
    assert fake.pw.chromium.launch_kwargs["headless"] is False
    assert "--start-maximized" in fake.pw.chromium.launch_kwargs["args"]
    assert DEFAULT_BROWSER_ARGS[0] in fake.pw.chromium.launch_kwargs["args"]

    session.stop()
    assert fake.pw.stopped is True
    assert fake.pw.chromium.browser.closed is True
    assert session._page is None


def test_inject_firefox_cookies(monkeypatch) -> None:
    session = BrowserSession(_config())
    context = _FakeContext()

    monkeypatch.setattr(
        "mihoyo_toolkit.scrapers.browser.load_firefox_cookies",
        lambda domain_filter=None: [{"name": "a", "value": "b"}],
    )
    session._inject_firefox_cookies(context)
    assert context.added_cookies == [[{"name": "a", "value": "b"}]]

    monkeypatch.setattr(
        "mihoyo_toolkit.scrapers.browser.load_firefox_cookies",
        lambda domain_filter=None: [],
    )
    session._inject_firefox_cookies(context)
    assert len(context.added_cookies) == 1


def test_goto_and_content(monkeypatch) -> None:
    session = BrowserSession(_config(wait_seconds=0.0))
    session._page = _FakePage()

    session.goto()
    assert session.page.goto_url == "https://example.com"
    assert session.page.waited is True

    session.goto("https://other.example.com")
    assert session.page.goto_url == "https://other.example.com"
    assert session.content() == "<html>content</html>"


def test_scroll_to_bottom_until_stable() -> None:
    session = BrowserSession(_config(scroll_delay=0.0))
    session._page = _FakePage(heights=[1000, 1000, 1000, 1000])
    ticks: list[int] = []

    count = session.scroll_to_bottom(on_tick=ticks.append)

    assert count == 3
    assert ticks == [1, 2, 3]


def test_scroll_to_bottom_stopped_early() -> None:
    session = BrowserSession(_config(scroll_delay=0.0))
    session._page = _FakePage(heights=[1000, 1000])

    count = session.scroll_to_bottom(is_stopped=lambda: True)

    assert count == 1


def test_current_links() -> None:
    session = BrowserSession(_config())
    session._page = _FakePage()
    assert session.current_links() == ["https://example.com/link"]


def test_open_browser_context_manager(monkeypatch) -> None:
    fake = _FakeSyncPlaywright()
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake)

    with open_browser(_config()) as session:
        assert isinstance(session, BrowserSession)
        assert session._page is not None

    assert fake.pw.stopped is True


def test_config_output_filename_is_used(tmp_path: Path) -> None:
    # html_path 基于输出文件名解析
    session = BrowserSession(_config())
    assert session.config.output_filename == "page.html"
