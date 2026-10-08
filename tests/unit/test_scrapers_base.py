"""scrapers.base 单元测试（浏览器会话以假对象替换）。"""

from __future__ import annotations

from typing import Any

import mihoyo_toolkit.scrapers.base as base_module
from mihoyo_toolkit.scrapers.base import BaseScraper
from mihoyo_toolkit.scrapers.config import ScrapeConfig


class _DemoScraper(BaseScraper[dict[str, Any]]):
    """用于测试的最小抓取器。"""

    @property
    def name(self) -> str:
        return "demo"

    def extract_items_from_api(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        items = data.get("items", [])
        return items if isinstance(items, list) else []


class _FakePage:
    def __init__(self) -> None:
        self.handlers: list[tuple[str, Any]] = []
        self.goto_url: str | None = None

    def on(self, event: str, handler: Any) -> None:
        self.handlers.append((event, handler))

    def goto(self, url: str, timeout: int | None = None) -> None:
        self.goto_url = url


class _FakeSession:
    def __init__(self, config: ScrapeConfig, html: str = "<html>demo</html>") -> None:
        self.config = config
        self.page = _FakePage()
        self._html = html
        self.stopped = False
        self.ticks: list[int] = []

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stopped = True

    def goto(self, url: str | None = None) -> None:
        self.page.goto(url or self.config.url)

    def scroll_to_bottom(self, *, on_tick=None, is_stopped=None) -> int:
        if on_tick is not None:
            on_tick(1)
        self.ticks.append(1)
        return 1

    def content(self) -> str:
        return self._html


class _Response:
    def __init__(self, ok: bool, url: str, data: Any = None, *, broken: bool = False) -> None:
        self.ok = ok
        self.url = url
        self._data = data
        self._broken = broken

    def json(self) -> Any:
        if self._broken:
            raise ValueError("invalid json")
        return self._data


def _config(**overrides) -> ScrapeConfig:
    return ScrapeConfig.from_settings("https://example.com", "demo.html", **overrides)


def test_abstract_parse_not_implemented() -> None:
    scraper = _DemoScraper(_config())
    assert scraper.name == "demo"
    try:
        scraper.parse("<html>")
    except NotImplementedError:
        pass
    else:  # pragma: no cover - 不应发生
        raise AssertionError("parse 应抛 NotImplementedError")


def test_run_saves_html(monkeypatch, tmp_home) -> None:
    monkeypatch.setattr(base_module, "BrowserSession", _FakeSession)

    scraper = _DemoScraper(_config())
    html = scraper.run()

    assert html == "<html>demo</html>"
    assert scraper.html_path.read_text(encoding="utf-8") == "<html>demo</html>"


def test_setup_api_interception_filters_responses() -> None:
    scraper = _DemoScraper(_config(api_url_keywords=["getContentList"]))
    session = _FakeSession(scraper.config)
    scraper.setup_api_interception(session)

    event, handler = session.page.handlers[0]
    assert event == "response"

    handler(_Response(False, "https://x/getContentList"))  # 非 200
    handler(_Response(True, "https://x/other"))  # 关键字不匹配
    handler(_Response(True, "https://x/getContentList", broken=True))  # JSON 解析失败
    handler(_Response(True, "https://x/getContentList", {"items": []}))  # 无条目
    assert scraper._api_items == []

    handler(_Response(True, "https://x/getContentList", {"items": [{"url": "u1"}]}))
    assert scraper._api_items == [{"url": "u1"}]


def test_setup_api_interception_stop_on_existing() -> None:
    scraper = _DemoScraper(
        _config(
            api_url_keywords=["getContentList"],
            incremental_mode=True,
            existing_urls={"https://x/item/1"},
        )
    )
    session = _FakeSession(scraper.config)
    scraper.setup_api_interception(session)
    handler = session.page.handlers[0][1]

    handler(
        _Response(
            True,
            "https://x/getContentList",
            {"items": [{"url": "https://x/item/1"}]},
        )
    )
    assert scraper._stop_requested is True


def test_should_stop_and_item_url() -> None:
    scraper = _DemoScraper(_config(incremental_mode=True, existing_urls={"https://x/item/1"}))
    assert scraper._should_stop([{"url": "https://x/item/1"}]) is True
    assert scraper._should_stop([{"url": "https://x/item/2"}]) is False

    class _Obj:
        url = "https://x/item/3"

    assert BaseScraper._item_url(_Obj()) == "https://x/item/3"
    assert BaseScraper._item_url({"url": "u"}) == "u"
    assert BaseScraper._item_url(object()) == ""  # type: ignore[arg-type]


def test_check_api_or_har_with_api_items() -> None:
    scraper = _DemoScraper(_config(scraper_name="demo"))
    scraper._api_items = [{"url": "u"}]
    assert scraper.check_api_or_har() is None


def test_check_api_or_har_without_scraper_name() -> None:
    scraper = _DemoScraper(_config())
    assert scraper.check_api_or_har() is None


def test_check_api_or_har_uses_har(har_factory) -> None:
    har_factory("demo")
    scraper = _DemoScraper(_config(scraper_name="demo"))
    assert scraper.check_api_or_har() == "use_har"


def test_check_api_or_har_prints_instructions(capsys) -> None:
    scraper = _DemoScraper(_config(scraper_name="demo", api_domain_filter="mihoyo.com"))
    assert scraper.check_api_or_har() is None
    assert "HAR" in capsys.readouterr().out
