"""Firefox Cookie 加载工具（跨平台）。

从 Firefox 的 ``cookies.sqlite`` 读取 Cookie 并转换为 Playwright 格式，
实现米游社 / 微博免登录。
"""

from __future__ import annotations

import platform
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .logger import get_module_logger

logger = get_module_logger("cookie_loader")

_SAMESITE_MAP = {0: "None", 1: "Lax", 2: "Strict"}


def _firefox_profile_dirs() -> list[Path]:
    """返回当前平台候选的 Firefox Profiles 目录。"""
    home = Path.home()
    system = platform.system()
    dirs: list[Path] = []
    if system == "Windows":
        import os

        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(Path(appdata) / "Mozilla" / "Firefox" / "Profiles")
    elif system == "Darwin":
        dirs.append(home / "Library" / "Application Support" / "Firefox" / "Profiles")
    else:
        dirs.append(home / ".mozilla" / "firefox")
    return dirs


def find_firefox_profile() -> Path | None:
    """查找 Firefox 默认配置文件目录。

    优先 ``default-release`` / ``default``，否则回退到任意含 cookies.sqlite 的目录。
    """
    for profiles_dir in _firefox_profile_dirs():
        if not profiles_dir.is_dir():
            continue

        candidates = [p for p in profiles_dir.iterdir() if p.is_dir()]
        for profile in candidates:
            name = profile.name.lower()
            if ("default-release" in name or "default" in name) and (
                profile / "cookies.sqlite"
            ).is_file():
                return profile

        for profile in candidates:
            if (profile / "cookies.sqlite").is_file():
                return profile
    return None


def load_firefox_cookies(domain_filter: str | None = None) -> list[dict[str, Any]]:
    """从 Firefox 读取 Cookie。

    Args:
        domain_filter: 按域名过滤，例如 ``"weibo.com"``。

    Returns:
        Playwright 格式的 Cookie 列表；失败时返回空列表。
    """
    profile = find_firefox_profile()
    if profile is None:
        logger.warning("未找到 Firefox 配置文件")
        return []

    cookies_db = profile / "cookies.sqlite"
    if not cookies_db.is_file():
        logger.warning("Firefox cookie 数据库不存在")
        return []

    tmp_db = Path(tempfile.gettempdir()) / "mihoyo_firefox_cookies.sqlite"
    try:
        shutil.copy2(cookies_db, tmp_db)
    except OSError as exc:
        logger.warning("复制 cookie 数据库失败: %s", exc)
        return []

    cookies: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(tmp_db)
        try:
            query = (
                "SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite"
                " FROM moz_cookies"
            )
            params: list[str] = []
            if domain_filter:
                query += " WHERE host LIKE ?"
                params.append(f"%{domain_filter}%")
            rows = conn.execute(query, params).fetchall()
        finally:
            conn.close()

        for name, value, host, path, expiry, secure, http_only, samesite in rows:
            if not expiry or expiry <= 0:
                expires = -1
            elif expiry > 1_000_000_000_000:
                expires = int(expiry / 1000)
            else:
                expires = int(expiry)
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": host,
                    "path": path,
                    "expires": expires,
                    "secure": bool(secure),
                    "httpOnly": bool(http_only),
                    "sameSite": _SAMESITE_MAP.get(samesite, "Lax"),
                }
            )
    except sqlite3.Error as exc:
        logger.warning("读取 cookie 失败: %s", exc)
        return []
    finally:
        tmp_db.unlink(missing_ok=True)

    logger.info(
        "从 Firefox 加载 %d 条 cookie%s",
        len(cookies),
        f" (域名: {domain_filter})" if domain_filter else "",
    )
    return cookies


__all__ = ["find_firefox_profile", "load_firefox_cookies"]
