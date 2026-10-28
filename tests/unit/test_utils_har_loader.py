"""utils.har_loader 单元测试。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from mihoyo_toolkit.utils.har_loader import (
    HAR_SITES,
    auto_har_path,
    ensure_har_dirs,
    extract_api_patterns,
    find_har_file,
    get_har_dir,
    get_har_welcome_html,
    get_har_welcome_text,
    load_api_pattern_from_har,
    load_har_entries,
    parse_har_file,
    print_har_instructions,
    prune_auto_har_files,
)


def test_har_sites_structure() -> None:
    assert len(HAR_SITES) >= 4
    for site in HAR_SITES:
        assert {"name", "scraper_name", "url"} <= set(site)


def test_get_har_dir(tmp_home: Path) -> None:
    assert get_har_dir("news_genshin") == tmp_home / "har" / "news_genshin"


def test_ensure_har_dirs(tmp_home: Path) -> None:
    ensure_har_dirs()
    for site in HAR_SITES:
        assert get_har_dir(site["scraper_name"]).is_dir()


def test_find_har_file_missing(tmp_home: Path) -> None:
    assert find_har_file("news_genshin") is None


def test_find_har_file_present(har_factory) -> None:
    target = har_factory("news_genshin")
    assert find_har_file("news_genshin") == target


def test_auto_har_path(tmp_home: Path) -> None:
    path = auto_har_path("news_genshin", datetime(2026, 10, 28, 12, 34, 56))
    assert path == tmp_home / "har" / "news_genshin" / "auto-20261028-123456.har"
    assert path.parent.is_dir()


def test_find_har_file_prefers_newest_json_payload(har_factory, tmp_home: Path) -> None:
    manual = har_factory("news_genshin")
    os.utime(manual, (1_700_000_000, 1_700_000_000))

    empty_dir = get_har_dir("news_genshin")
    empty = empty_dir / "auto-20261028-000000.har"
    empty.write_text(json.dumps({"log": {"version": "1.2", "entries": []}}), encoding="utf-8")
    os.utime(empty, (1_700_000_100, 1_700_000_100))

    # 空录制文件更新，但应优先选择含 JSON 响应体的手动 HAR
    assert find_har_file("news_genshin") == manual


def test_prune_auto_har_files_keeps_newest(har_factory, tmp_home: Path) -> None:
    manual = har_factory("news_genshin")
    target_dir = get_har_dir("news_genshin")
    for index in range(4):
        path = target_dir / f"auto-2026100{index + 1}-000000.har"
        path.write_text("{}", encoding="utf-8")
        stamp = 1_700_000_000 + index
        os.utime(path, (stamp, stamp))

    prune_auto_har_files("news_genshin", 2)

    assert manual.exists()
    names = sorted(path.name for path in target_dir.iterdir())
    assert names == ["auto-20261003-000000.har", "auto-20261004-000000.har", "sample.har"]


def test_parse_har_file(sample_har_path: Path) -> None:
    entries = parse_har_file(sample_har_path)
    assert len(entries) == 1
    assert "getContentList" in entries[0]["request"]["url"]


def test_parse_har_file_invalid(tmp_path: Path) -> None:
    bad = tmp_path / "bad.har"
    bad.write_text("not a json at all", encoding="utf-8")
    assert parse_har_file(bad) == []


def test_load_har_entries(har_factory) -> None:
    har_factory("news_genshin")
    payloads = load_har_entries("news_genshin")
    assert len(payloads) == 1
    assert payloads[0]["data"]["iTotal"] == 2


def test_load_har_entries_no_file(tmp_home: Path) -> None:
    assert load_har_entries("does_not_exist") == []


def test_extract_api_patterns(sample_har_path: Path) -> None:
    patterns = extract_api_patterns(sample_har_path)
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern["method"] == "GET"
    assert pattern["has_json_response"] is True
    assert pattern["params"]["iChanId"] == "719"

    assert extract_api_patterns(sample_har_path, ["nomatch.example"]) == []


def test_load_api_pattern_from_har(har_factory) -> None:
    har_factory("news_genshin")
    pattern = load_api_pattern_from_har("news_genshin", ["getContentList"])
    assert pattern is not None
    assert pattern["domain"] == "act-api-takumi-static.mihoyo.com"
    assert pattern["url_pattern"] == "getContentList"


def test_load_api_pattern_from_har_missing(tmp_home: Path) -> None:
    assert load_api_pattern_from_har("nope") is None


def test_print_har_instructions(har_factory, capsys) -> None:
    print_har_instructions("news_genshin", "https://example.com", ["mihoyo.com"])
    captured = capsys.readouterr()
    assert "HAR" in captured.out
    assert "mihoyo.com" in captured.out


def test_get_har_welcome_text() -> None:
    text = get_har_welcome_text()
    assert "米游社工具箱" in text
    assert "原神新闻" in text


def test_get_har_welcome_html() -> None:
    html = get_har_welcome_html()
    assert html.startswith("<h3>")
    assert "米游社工具箱" in html
