import os
import sqlite3
import shutil
import tempfile
from typing import List, Dict, Optional, Tuple
from pathlib import Path


def _profiles_ini_default(profiles_dir: str) -> Optional[str]:
    """解析 Firefox profiles.ini，定位 Path= 指定的 Default profile 目录"""
    ini_path = os.path.join(profiles_dir, "profiles.ini")
    if not os.path.isfile(ini_path):
        return None
    try:
        current_section = {}
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith(";") or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section_name = line[1:-1].strip()
                    if section_name.lower().startswith("profile"):
                        current_section = {}
                    else:
                        current_section = None
                    continue
                if current_section is None or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                current_section[k.strip()] = v.strip()
                if current_section.get("Default") == "1" or current_section.get("Name") == "default-release":
                    rel = current_section.get("Path")
                    if rel:
                        is_relative = current_section.get("IsRelative", "1") == "1"
                        candidate = os.path.join(profiles_dir, rel) if is_relative else rel
                        if os.path.isdir(candidate):
                            return candidate
    except Exception:
        return None
    # 兜底：找第一个 StartWithLastProfile=1 对应 Profile 的 Path
    try:
        current_section = {}
        start_with_last = None
        profile_sections = []
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section_name = line[1:-1].strip()
                    if section_name.lower().startswith("profile"):
                        current_section = {}
                        profile_sections.append(current_section)
                    elif section_name.lower() == "general":
                        current_section = "GENERAL"
                    else:
                        current_section = None
                    continue
                if current_section == "GENERAL" and line.startswith("StartWithLastProfile="):
                    start_with_last = line.split("=", 1)[1].strip()
                elif isinstance(current_section, dict) and "=" in line:
                    k, _, v = line.partition("=")
                    current_section[k.strip()] = v.strip()
        if start_with_last is not None and profile_sections:
            try:
                idx = int(start_with_last)
                if 0 <= idx - 1 < len(profile_sections):
                    sec = profile_sections[idx - 1]
                    rel = sec.get("Path")
                    is_rel = sec.get("IsRelative", "1") == "1"
                    candidate = os.path.join(profiles_dir, rel) if is_rel else rel
                    if os.path.isdir(candidate):
                        return candidate
            except Exception:
                pass
    except Exception:
        return None
    return None


def _scan_profiles_dir(profiles_dir: str) -> Optional[str]:
    if not os.path.isdir(profiles_dir):
        return None
    # 优先 profiles.ini
    ini_default = _profiles_ini_default(profiles_dir)
    if ini_default:
        cookies_db = os.path.join(ini_default, "cookies.sqlite")
        if os.path.exists(cookies_db):
            return ini_default
    # 其次名字包含 default-release 且有 cookies.sqlite
    for entry in sorted(os.listdir(profiles_dir)):
        entry_path = os.path.join(profiles_dir, entry)
        if os.path.isdir(entry_path) and ("default-release" in entry or "default" in entry):
            if os.path.exists(os.path.join(entry_path, "cookies.sqlite")):
                return entry_path
    # 再次兜底：任何包含 cookies.sqlite 的子目录
    for entry in sorted(os.listdir(profiles_dir)):
        entry_path = os.path.join(profiles_dir, entry)
        if os.path.isdir(entry_path) and os.path.exists(os.path.join(entry_path, "cookies.sqlite")):
            return entry_path
    return None


def _find_windows_profile() -> Optional[str]:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None
    profiles_dir = os.path.join(appdata, "Mozilla", "Firefox", "Profiles")
    return _scan_profiles_dir(profiles_dir)


def _find_macos_profile() -> Optional[str]:
    home = os.path.expanduser("~")
    profiles_dir = os.path.join(home, "Library", "Application Support", "Firefox", "Profiles")
    return _scan_profiles_dir(profiles_dir)


def _find_linux_profile() -> Optional[str]:
    """Linux / Termux / proot-distro 的 Firefox 配置目录扫描。
    候选顺序：
    1) ~/.mozilla/firefox/  —— 绝大多数桌面 Linux + proot-distro 里的 Ubuntu/Debian/Arch Firefox
    2) $SNAP_USER_DATA/.mozilla/firefox/ —— Snap 安装的 Firefox
    3) $FLATPAK_HOST_HOME/.mozilla/firefox/ 或 ~/.var/app/org.mozilla.firefox/.mozilla/firefox —— Flatpak Firefox
    4) /data/data/com.zerotermux/files/home/.mozilla/firefox —— ZeroTermux 主目录下安装过 Firefox（通常是 proot-distro）
    5) /data/data/com.termux/files/home/.mozilla/firefox —— 普通 Termux 主目录
    """
    candidates = []
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".mozilla", "firefox"))
    snap = os.environ.get("SNAP_USER_DATA")
    if snap:
        candidates.append(os.path.join(snap, ".mozilla", "firefox"))
    flatpak_home = os.environ.get("FLATPAK_HOST_HOME")
    if flatpak_home:
        candidates.append(os.path.join(flatpak_home, ".mozilla", "firefox"))
    candidates.append(os.path.join(home, ".var", "app", "org.mozilla.firefox", ".mozilla", "firefox"))
    prefix = os.environ.get("PREFIX")
    if prefix and ("termux" in prefix.lower() or "zerotermux" in prefix.lower()):
        # Termux 自身的 $HOME 一般已经在 expanduser('~') 覆盖，但再兜底
        candidates.append(os.path.join(prefix.rstrip("/usr"), "files", "home", ".mozilla", "firefox"))
        # proot-distro 中的 Ubuntu/Debian 往往把宿主 home 作为子路径：/data/data/.../home/proot-distro/ubuntu/root/...
        candidates.append(os.path.join(prefix.rstrip("/usr"), "files", "home", ".proot-distro", "ubuntu", "root", ".mozilla", "firefox"))
        candidates.append(os.path.join(prefix.rstrip("/usr"), "files", "home", ".proot-distro", "debian", "root", ".mozilla", "firefox"))
        candidates.append(os.path.join(prefix.rstrip("/usr"), "files", "home", ".proot-distro", "ubuntu", "home", ".mozilla", "firefox"))
        candidates.append(os.path.join(prefix.rstrip("/usr"), "files", "home", ".proot-distro", "debian", "home", ".mozilla", "firefox"))
    for c in candidates:
        found = _scan_profiles_dir(c)
        if found:
            return found
    return None


def find_firefox_profile() -> Optional[str]:
    """查找 Firefox 默认配置文件路径
    支持 Windows / macOS / Linux / ZeroTermux / Termux / proot-distro / Snap / Flatpak 多套安装路径。"""
    # 环境变量强覆盖（便于脚本化注入）
    env_override = os.environ.get("MIHOYO_TOOLKIT_FIREFOX_PROFILE")
    if env_override and os.path.isdir(env_override):
        cookies_db = os.path.join(env_override, "cookies.sqlite")
        if os.path.exists(cookies_db):
            return env_override
    import sys
    platform_sys = sys.platform.lower()
    if platform_sys.startswith("win"):
        return _find_windows_profile()
    if platform_sys == "darwin":
        return _find_macos_profile()
    # 所有 Unix-like 都走 Linux 分支（含 Android/Linux/Termux）
    return _find_linux_profile()


def load_firefox_cookies(domain_filter: str = None) -> List[Dict[str, str]]:
    """
    从 Firefox 读取 cookie

    Args:
        domain_filter: 按域名过滤，例如 "weibo.com"

    Returns:
        Playwright 格式的 cookie 列表
    """
    profile_path = find_firefox_profile()
    if not profile_path:
        print("[WARN] 未找到 Firefox 配置文件")
        return []

    cookies_db = os.path.join(profile_path, "cookies.sqlite")
    if not os.path.exists(cookies_db):
        print("[WARN] Firefox cookie 数据库不存在")
        return []

    tmp_db = os.path.join(tempfile.gettempdir(), "firefox_cookies_tmp.sqlite")
    try:
        shutil.copy2(cookies_db, tmp_db)
    except Exception as e:
        print(f"[WARN] 复制 cookie 数据库失败: {e}")
        return []

    cookies = []
    try:
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()

        query = "SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite FROM moz_cookies"
        params = []

        if domain_filter:
            query += " WHERE host LIKE ?"
            params.append(f"%{domain_filter}%")

        cursor.execute(query, params)
        rows = cursor.fetchall()

        samesite_map = {0: "None", 1: "Lax", 2: "Strict"}

        for row in rows:
            name, value, host, path, expiry, is_secure, is_httponly, samesite = row

            if expiry is None or expiry <= 0:
                expires_val = -1
            else:
                if expiry > 1000000000000:
                    expires_val = int(expiry / 1000)
                else:
                    expires_val = int(expiry)

            same_site_str = samesite_map.get(samesite, "Lax")

            cookie = {
                "name": name,
                "value": value,
                "domain": host,
                "path": path,
                "expires": expires_val,
                "secure": bool(is_secure),
                "httpOnly": bool(is_httponly),
                "sameSite": same_site_str
            }
            cookies.append(cookie)

        conn.close()
    except Exception as e:
        print(f"[WARN] 读取 cookie 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)
        except:
            pass

    print(f"[INFO] 从 Firefox 加载了 {len(cookies)} 条 cookie" + (f" (域名: {domain_filter})" if domain_filter else ""))
    return cookies
