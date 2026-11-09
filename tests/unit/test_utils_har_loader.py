"""utils.har_loader 单元测试。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from mihoyo_toolkit.utils.har_loader import (
    HAR_SITES,
    auto_har_path,
    cleanup_har_files,
    describe_har_files,
    ensure_har_dirs,
    extract_api_patterns,
    find_har_file,
    format_har_report,
    get_har_dir,
    get_har_welcome_html,
    get_har_welcome_text,
    har_saved_at,
    har_site_status,
    load_api_pattern_from_har,
    load_har_entries,
    parse_har_file,
    print_har_instructions,
    prune_auto_har_files,
    update_har_files,
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
    assert "--har" in text


def test_get_har_welcome_html() -> None:
    html = get_har_welcome_html()
    assert html.startswith("<h3>")
    assert "米游社工具箱" in html
    assert "--har" in html


# ---------------------------------------------------------------------- #
#  HAR 保存时间 / 目录状态 / 清理
# ---------------------------------------------------------------------- #
def _write_har(path: Path, *, mtime: float | None = None) -> Path:
    """写入一个最小 HAR 文件（可选指定 mtime），返回路径。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_har_saved_at_reads_auto_filename(tmp_home: Path) -> None:
    path = _write_har(get_har_dir("user") / "auto-20261031-002005.har", mtime=1_700_000_000)
    assert har_saved_at(path) == datetime(2026, 10, 31, 0, 20, 5)


def test_har_saved_at_reads_browser_filename(tmp_home: Path) -> None:
    path = _write_har(
        get_har_dir("user") / "www.miyoushe.com_Archive [26-11-09 16-10-58].har",
        mtime=1_700_000_000,
    )
    assert har_saved_at(path) == datetime(2026, 11, 9, 16, 10, 58)


def test_har_saved_at_falls_back_to_mtime(tmp_home: Path) -> None:
    path = _write_har(get_har_dir("user") / "sample.har", mtime=1_700_000_000)
    assert har_saved_at(path) == datetime.fromtimestamp(1_700_000_000)


def test_describe_har_files_sorts_by_saved_at(har_factory, tmp_home: Path) -> None:
    manual = har_factory("news_genshin")
    os.utime(manual, (1_700_000_000, 1_700_000_000))
    _write_har(get_har_dir("news_genshin") / "auto-20261101-000000.har")

    infos = describe_har_files("news_genshin")

    assert [info.name for info in infos] == ["auto-20261101-000000.har", "sample.har"]
    assert infos[0].auto is True
    assert infos[1].kind == "手动导出"


def test_describe_har_files_missing_dir(tmp_home: Path) -> None:
    assert describe_har_files("does_not_exist") == []


def test_cleanup_har_files_keeps_newest_and_manual(har_factory, tmp_home: Path) -> None:
    target_dir = get_har_dir("user")
    manual = _write_har(target_dir / "www.miyoushe.com_Archive [26-10-28 13-15-31].har")
    stale = _write_har(target_dir / "auto-20261030-000000.har")
    newest = _write_har(target_dir / "auto-20261101-000000.har")

    result = cleanup_har_files(keep=1)

    assert stale.exists() is False
    # 最新的自动录制优先保留，但最新的手动导出也不会被删除
    assert newest.exists() is True
    assert manual.exists() is True
    assert result.removed == [stale]


def test_cleanup_har_files_respects_keep_count(tmp_home: Path) -> None:
    target_dir = get_har_dir("weibo")
    files = [_write_har(target_dir / f"auto-2026100{index + 1}-000000.har") for index in range(3)]

    result = cleanup_har_files(keep=2)

    assert result.removed == [files[0]]
    assert files[1].exists() is True
    assert files[2].exists() is True


def test_cleanup_har_files_nested_dirs(tmp_home: Path) -> None:
    nested = get_har_dir("tutorial/zh_cn")
    stale = _write_har(nested / "auto-20261030-000000.har")
    newest = _write_har(nested / "auto-20261031-000000.har")

    result = cleanup_har_files(keep=1)

    assert stale.exists() is False
    assert newest.exists() is True
    assert result.removed == [stale]


def test_cleanup_har_files_empty_har_dir(tmp_home: Path) -> None:
    ensure_har_dirs()
    result = cleanup_har_files(keep=1)
    assert result.removed == []
    assert result.kept == []


def test_har_site_status(har_factory, tmp_home: Path) -> None:
    har_factory("news_genshin")

    statuses = har_site_status()

    assert len(statuses) == len(HAR_SITES)
    genshin = next(item for item in statuses if item.scraper_name == "news_genshin")
    assert genshin.current is not None
    assert genshin.current.name == "sample.har"
    assert genshin.url == "https://ys.mihoyo.com/main/news"
    weibo = next(item for item in statuses if item.scraper_name == "weibo")
    assert weibo.current is None
    assert weibo.extra_count == 0
    assert weibo.url.startswith("https://weibo.com/")


def test_har_site_status_uses_configured_user_url(tmp_home: Path) -> None:
    user = next(item for item in har_site_status() if item.scraper_name == "user")
    assert user.url == "https://www.miyoushe.com/ys/accountCenter/postList?id=10000000"


def test_update_har_files_reports_sites(har_factory, tmp_home: Path) -> None:
    target_dir = get_har_dir("news_genshin")
    manual = har_factory("news_genshin")
    manual_time = datetime(2026, 10, 30).timestamp()
    os.utime(manual, (manual_time, manual_time))
    stale = _write_har(target_dir / "auto-20261030-000000.har")
    newest = _write_har(target_dir / "auto-20261101-000000.har")

    report = update_har_files(keep=1)

    assert report.removed == [stale]
    assert report.kept and set(report.kept) >= {manual, newest}
    status = next(item for item in report.sites if item.scraper_name == "news_genshin")
    assert status.current is not None
    assert status.current.name == "auto-20261101-000000.har"


def test_format_har_report(har_factory, tmp_home: Path) -> None:
    har_factory("news_genshin")

    text = "\n".join(format_har_report(update_har_files(keep=1)))

    assert "已清理旧文件 0 个" in text
    assert "原神新闻" in text
    assert "sample.har" in text
    assert "缺失" in text  # 未放 HAR 的站点给出缺失提示
    assert "页面: https://ys.mihoyo.com/main/news" in text
    assert "页面: https://weibo.com/" in text
