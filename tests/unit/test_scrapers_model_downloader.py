"""scrapers.model_downloader 单元测试（纯函数 + 打桩 IO）。"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import mihoyo_toolkit.scrapers.model_downloader as md
from mihoyo_toolkit.scrapers.model_downloader import (
    ModelItem,
    VersionInfo,
    download_file,
    extract_download_links_from_html,
    fetch_page_html,
    match_links_to_characters,
    parse_create_plan,
    run_model_download,
)

PLAN_MD = """
# 原神模型计划

### 完整列表
```text
V5.0 欢夏！邪龙？童话国！
[*链接] https://example.com/page-a
[*序号] 角色
[*角色名称]
1 角色A、角色B
https://example.com/a.zip

---

V5.1 夜兰的传说
1 角色C
https://example.com/b.zip

---
```

其他说明。
"""


# ---------------------------------------------------------------------- #
#  create-plan.md 解析
# ---------------------------------------------------------------------- #
def test_parse_create_plan(tmp_path: Path) -> None:
    plan = tmp_path / "create-plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    versions = parse_create_plan(plan)
    assert [v.version for v in versions] == ["V5.0", "V5.1"]
    assert versions[0].version_name == "欢夏！邪龙？童话国！"
    assert versions[0].url == "https://example.com/a.zip"
    assert versions[0].characters == ["角色A", "角色B"]
    assert versions[1].characters == ["角色C"]


def test_parse_create_plan_missing_file(tmp_path: Path) -> None:
    assert parse_create_plan(tmp_path / "nope.md") == []


def test_parse_create_plan_without_code_block(tmp_path: Path) -> None:
    plan = tmp_path / "create-plan.md"
    plan.write_text("# 标题\n没有代码块", encoding="utf-8")
    assert parse_create_plan(plan) == []


def test_parse_create_plan_default_path(tmp_home: Path) -> None:
    # docs/create-plan.md 不存在
    assert parse_create_plan() == []


# ---------------------------------------------------------------------- #
#  URL / 链接提取
# ---------------------------------------------------------------------- #
def test_normalize_url() -> None:
    assert md._normalize_url("https://x/a.zip") == "https://x/a.zip"
    assert md._normalize_url("//cdn.example.com/a.zip") == "https://cdn.example.com/a.zip"
    assert md._normalize_url("example.com/a.zip") == "https://example.com/a.zip"
    assert md._normalize_url("前缀 https://x/a.zip") == "https://x/a.zip"


def test_extract_links_from_state() -> None:
    state = {
        "a": {"link": "https://x/a.zip", "text": "T"},
        "b": [{"link": "https://x/b.rar"}],
        "c": {"link": "https://x/c.png"},
    }
    results = md._extract_links_from_state(state)
    assert {r["link"] for r in results} == {"https://x/a.zip", "https://x/b.rar"}


def test_extract_download_links_from_html() -> None:
    html = """
    <html><body>
      <a href="https://dl.example.com/a.zip" data-report-click="caster-a-角色A模型下载">A</a>
      <a href="https://dl.example.com/a.zip">重复</a>
      <script>window.__initialState = {"state": {"link": "https://dl.example.com/b.zip",
      "title": "角色B"}};</script>
      原始链接 https://cdn.example.com/c.7z
    </body></html>
    """
    links = extract_download_links_from_html(html, "https://page")
    assert [link["url"] for link in links] == [
        "https://dl.example.com/a.zip",
        "https://dl.example.com/b.zip",
        "https://cdn.example.com/c.7z",
    ]
    assert links[0]["report_click"] == "caster-a-角色A模型下载"
    assert links[0]["order"] == 0


def test_extract_download_links_invalid_state() -> None:
    html = "<script>window.__initialState = {not json};</script>"
    assert extract_download_links_from_html(html) == []


# ---------------------------------------------------------------------- #
#  角色名匹配
# ---------------------------------------------------------------------- #
def test_pinyin_helpers() -> None:
    assert md._get_character_pinyin("钟离（岩）").lower() == "zhongli"
    assert md._get_character_pinyin_initials("钟离（岩）").lower() == "zl"


def test_extract_character_from_report_click() -> None:
    assert md._extract_character_from_report_click("") == ""
    assert md._extract_character_from_report_click("caster-a-钟离模型下载") == "钟离"
    assert md._extract_character_from_report_click("下载-钟离") == "钟离"
    assert md._extract_character_from_report_click("下载模型1") == ""


def test_extract_character_from_filename() -> None:
    assert md._extract_character_from_filename("【钟离】.zip") == "钟离"
    assert md._extract_character_from_filename("x.zip") == ""


def test_match_char() -> None:
    assert md._match_char("钟离", ["钟离", "岩王帝君"]) == "钟离"
    assert md._match_char("岩", ["钟离"]) is None


def test_match_links_to_characters_report_click_and_filename() -> None:
    links = [
        {"url": "u1", "filename": "a.zip", "report_click": "caster-a-钟离模型下载"},
        {"url": "u2", "filename": "【胡桃】.zip", "report_click": ""},
        {"url": "u3", "filename": "unknown.zip", "report_click": ""},
    ]
    items = match_links_to_characters(links, ["钟离", "胡桃"])
    assert items[0].character == "钟离" and items[0].matched is True
    assert items[1].character == "胡桃" and items[1].matched is True
    assert items[2].matched is False


def test_match_links_to_characters_pinyin_and_order_fallback() -> None:
    links = [
        {"url": "u1", "filename": "hutao.zip", "report_click": ""},
        {"url": "u2", "filename": "unmatched.zip", "report_click": ""},
    ]
    items = match_links_to_characters(links, ["胡桃", "钟离"])
    assert items[0].character == "胡桃"
    # 顺序兜底：剩余角色指派给未匹配项
    assert items[1].character == "钟离"
    assert items[1].matched is True


def test_match_links_to_characters_initials() -> None:
    links = [{"url": "u1", "filename": "zl.zip", "report_click": ""}]
    items = match_links_to_characters(links, ["钟离"])
    assert items[0].character == "钟离"


def test_dataclasses() -> None:
    item = ModelItem(version="v", version_name="n", character="c", url="u", filename="f")
    assert item.matched is True
    version = VersionInfo(version="V1.0", version_name="n", url="u", characters=["c"])
    assert version.characters == ["c"]


# ---------------------------------------------------------------------- #
#  下载
# ---------------------------------------------------------------------- #
def test_download_file_existing(tmp_path: Path) -> None:
    target = tmp_path / "f.zip"
    target.write_text("x", encoding="utf-8")
    assert download_file("https://x", target) is True


def test_download_file_success(tmp_path: Path, monkeypatch) -> None:
    def fake_stream(url, save_path, timeout) -> int:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(b"data")
        return 4

    monkeypatch.setattr(md, "_stream_to_file", fake_stream)
    target = tmp_path / "sub" / "f.zip"
    assert download_file("https://x", target) is True
    assert target.read_bytes() == b"data"


def test_download_file_failure(tmp_path: Path, monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise OSError("net down")

    monkeypatch.setattr(md, "_stream_to_file", boom)
    target = tmp_path / "f.zip"
    assert download_file("https://x", target) is False
    assert not target.exists()


def test_fetch_page_html(monkeypatch) -> None:
    class FakeSession:
        def goto(self, url=None) -> None:
            pass

        def content(self) -> str:
            return "<html>page</html>"

    @contextmanager
    def fake_open(config):
        yield FakeSession()

    monkeypatch.setattr(md, "open_browser", fake_open)
    assert fetch_page_html("https://x") == "<html>page</html>"


def test_run_model_download(monkeypatch, tmp_home: Path) -> None:
    version = VersionInfo(version="V5.0", version_name="n", url="https://page", characters=["钟离"])
    monkeypatch.setattr(md, "parse_create_plan", lambda: [version])
    monkeypatch.setattr(
        md,
        "fetch_page_html",
        lambda url: '<a href="https://dl/a.zip" data-report-click="caster-a-钟离模型下载">A</a>',
    )
    downloaded: list[Path] = []
    monkeypatch.setattr(
        md,
        "download_file",
        lambda url, save_path, timeout=300.0: downloaded.append(save_path) or True,
    )

    assert run_model_download() == 1
    assert downloaded and downloaded[0].name == "a.zip"


def test_run_model_download_no_versions(monkeypatch) -> None:
    monkeypatch.setattr(md, "parse_create_plan", lambda: [])
    assert run_model_download() == 0


def test_run_model_download_page_error(monkeypatch) -> None:
    version = VersionInfo(version="V5.0", version_name="n", url="https://page", characters=["钟离"])
    monkeypatch.setattr(md, "parse_create_plan", lambda: [version])

    def boom(url):
        raise RuntimeError("no page")

    monkeypatch.setattr(md, "fetch_page_html", boom)
    assert run_model_download() == 0


def test_run_model_download_unmatched_skipped(monkeypatch) -> None:
    version = VersionInfo(version="V5.0", version_name="n", url="https://page", characters=[])
    monkeypatch.setattr(md, "parse_create_plan", lambda: [version])
    monkeypatch.setattr(md, "fetch_page_html", lambda url: '<a href="https://dl/a.zip">A</a>')
    monkeypatch.setattr(md, "download_file", lambda url, save_path, timeout=300.0: True)

    assert run_model_download() == 0
