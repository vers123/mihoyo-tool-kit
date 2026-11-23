"""utils.cookie_loader 单元测试。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mihoyo_toolkit.utils import cookie_loader
from mihoyo_toolkit.utils.cookie_loader import find_firefox_profile, load_firefox_cookies


def _make_cookies_db(profile: Path) -> None:
    profile.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(profile / "cookies.sqlite")
    conn.execute(
        "CREATE TABLE moz_cookies ("
        "name TEXT, value TEXT, host TEXT, path TEXT,"
        "expiry INTEGER, isSecure INTEGER, isHttpOnly INTEGER, sameSite INTEGER)"
    )
    conn.executemany(
        "INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("session", "v1", "weibo.com", "/", 0, 1, 0, 1),
            ("persist", "v2", "miyoushe.com", "/", 1_700_000_000, 0, 1, 2),
            ("ms_expiry", "v3", "weibo.com", "/", 1_700_000_000_000, 1, 1, 0),
        ],
    )
    conn.commit()
    conn.close()


def test_find_firefox_profile_none_when_no_dirs(monkeypatch) -> None:
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [])
    assert find_firefox_profile() is None


def test_load_firefox_cookies_without_profile(monkeypatch) -> None:
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [])
    assert load_firefox_cookies() == []


def test_find_firefox_profile_prefers_default(tmp_path: Path, monkeypatch) -> None:
    profiles = tmp_path / "Profiles"
    _make_cookies_db(profiles / "abc123.default-release")
    _make_cookies_db(profiles / "other")
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    found = find_firefox_profile()
    assert found is not None
    assert "default-release" in found.name


def test_find_firefox_profile_fallback_any_profile(tmp_path: Path, monkeypatch) -> None:
    profiles = tmp_path / "Profiles"
    _make_cookies_db(profiles / "random")
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    found = find_firefox_profile()
    assert found is not None
    assert found.name == "random"


def test_find_firefox_profile_ignores_profile_without_db(tmp_path: Path, monkeypatch) -> None:
    profiles = tmp_path / "Profiles"
    (profiles / "empty.default").mkdir(parents=True)
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])
    assert find_firefox_profile() is None


def test_load_firefox_cookies_parses_rows(tmp_path: Path, monkeypatch) -> None:
    profiles = tmp_path / "Profiles"
    _make_cookies_db(profiles / "abc.default-release")
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    cookies = {c["name"]: c for c in load_firefox_cookies()}
    assert set(cookies) == {"session", "persist", "ms_expiry"}
    assert cookies["session"]["expires"] == -1
    assert cookies["session"]["sameSite"] == "Lax"
    assert cookies["persist"]["expires"] == 1_700_000_000
    assert cookies["persist"]["sameSite"] == "Strict"
    assert cookies["ms_expiry"]["expires"] == 1_700_000_000
    assert cookies["ms_expiry"]["sameSite"] == "None"


def test_load_firefox_cookies_domain_filter(tmp_path: Path, monkeypatch) -> None:
    profiles = tmp_path / "Profiles"
    _make_cookies_db(profiles / "abc.default-release")
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    cookies = load_firefox_cookies(domain_filter="weibo.com")
    assert {c["name"] for c in cookies} == {"session", "ms_expiry"}


def test_load_firefox_cookies_when_db_missing(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / "Profiles" / "abc.default-release"
    profile.mkdir(parents=True)
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profile.parent])
    # find_firefox_profile 找不到含 cookies.sqlite 的目录
    assert load_firefox_cookies() == []


def test_find_firefox_profile_handles_missing_dir(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "nope"
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [missing])
    assert find_firefox_profile() is None


# ---------------------------------------------------------------------- #
#  临时工作区与外部只读
# ---------------------------------------------------------------------- #
def test_cookie_db_is_copied_to_temp_workspace_and_cleaned(tmp_path: Path, monkeypatch) -> None:
    """源库只读：复制到临时工作区读取，结束后临时目录被清理。"""
    profiles = tmp_path / "Profiles"
    profile = profiles / "abc.default-release"
    _make_cookies_db(profile)
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    created: list[Path] = []
    original = cookie_loader.temp_workspace

    import contextlib

    @contextlib.contextmanager
    def _spy():
        with original() as workdir:
            created.append(workdir)
            yield workdir

    monkeypatch.setattr(cookie_loader, "temp_workspace", _spy)
    cookies = load_firefox_cookies()

    assert cookies
    assert created and not created[0].exists()


def test_source_profile_is_not_modified(tmp_path: Path, monkeypatch) -> None:
    """读取过程中不修改 Firefox 源数据库（mtime 与内容都不变）。"""
    profiles = tmp_path / "Profiles"
    profile = profiles / "abc.default-release"
    _make_cookies_db(profile)
    source = profile / "cookies.sqlite"
    before = source.read_bytes()
    before_mtime = source.stat().st_mtime
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    load_firefox_cookies()

    assert source.read_bytes() == before
    assert source.stat().st_mtime == before_mtime


def test_failed_copy_returns_empty(tmp_path: Path, monkeypatch) -> None:
    """复制失败时返回空列表，不抛出异常。"""
    profiles = tmp_path / "Profiles"
    profile = profiles / "abc.default-release"
    _make_cookies_db(profile)
    monkeypatch.setattr(cookie_loader, "_firefox_profile_dirs", lambda: [profiles])

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(cookie_loader.shutil, "copy2", _boom)
    assert load_firefox_cookies() == []
