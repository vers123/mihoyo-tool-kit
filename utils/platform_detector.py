"""
平台环境检测模块
用于识别当前运行环境是否为 ZeroTermux / Termux（Android）
并返回对应的环境元信息。
"""

import os
import sys
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


ZERO_TERMUXTARGET_PACKAGE_NAMES = (
    "com.zerotermux",
    "com.termux",
    "com.termux.api",
)

ANDROID_KERNEL_MARKERS = (
    "android",
    "lineageos",
)


@dataclass
class PlatformInfo:
    is_android: bool = False
    is_termux: bool = False
    is_zerotermux: bool = False
    is_proot_distro: bool = False            # 处于 proot-distro 容器中
    proot_distro_name: Optional[str] = None   # e.g. "ubuntu", "debian"
    arch: str = ""
    termux_prefix: Optional[str] = None       # $PREFIX，Termux 中是 /data/data/.../files/usr
    termux_home: Optional[str] = None         # $HOME，Termux 下 /data/data/.../files/home
    zerotermux_version: Optional[str] = None  # ZeroTermux 的版本号若可探测
    has_display: bool = False                 # $DISPLAY / $WAYLAND_DISPLAY 是否存在
    memory_total_mb: int = 0                  # 系统总内存估算
    recommended_headless: bool = True         # 是否推荐 headless 运行
    recommended_extra_browser_args: tuple = ()

    @property
    def needs_mobile_optimized_browser(self) -> bool:
        """是否需要启用移动端优化的浏览器参数"""
        return self.is_termux or self.is_android or self.is_proot_distro


def _detect_arch() -> str:
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return "aarch64"
    if machine.startswith("arm"):
        return "arm"
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    if machine in ("i386", "i686"):
        return "x86"
    return machine or "unknown"


def _detect_termux_prefix() -> Optional[str]:
    prefix = os.environ.get("PREFIX")
    if prefix:
        return prefix
    candidates = [
        "/data/data/com.zerotermux/files/usr",
        "/data/data/com.termux/files/usr",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def _detect_termux_home() -> Optional[str]:
    home = os.environ.get("HOME")
    if home and ("com.zerotermux" in home or "com.termux" in home):
        return home
    candidates = [
        "/data/data/com.zerotermux/files/home",
        "/data/data/com.termux/files/home",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def _detect_is_android(info: PlatformInfo, arch: str) -> None:
    uname_s = platform.system().lower()
    android_filesystem_markers = ["/system", "/vendor", "/data/app"]
    if "android" in uname_s:
        info.is_android = True
        return
    kernel_release = platform.release().lower()
    if any(m in kernel_release for m in ANDROID_KERNEL_MARKERS):
        info.is_android = True
        return
    if info.termux_prefix:
        info.is_android = True
        return
    if arch in ("aarch64", "arm") and any(os.path.isdir(p) for p in android_filesystem_markers):
        info.is_android = True


def _detect_is_termux(info: PlatformInfo) -> None:
    if info.termux_prefix:
        info.is_termux = True
        if "zerotermux" in info.termux_prefix:
            info.is_zerotermux = True
    if os.environ.get("TERMUX_VERSION"):
        info.is_termux = True
    if os.environ.get("ZEROTERMUXTARGET") or os.environ.get("ZERO_TERMUXTARGET"):
        info.is_termux = True
        info.is_zerotermux = True


def _detect_is_proot(info: PlatformInfo) -> None:
    # proot 进程会存在 /proc/self/status 中的 TracerPid !=0，或存在 PROOTED=1
    if os.environ.get("PROOTED") == "1":
        info.is_proot_distro = True
    if os.environ.get("APP_IMAGE_SANDBOX_PATH"):
        info.is_proot_distro = True
    try:
        status = Path("/proc/self/status").read_text(errors="ignore")
        # proot 下会显示 name/proctitle 被修改；同时检查 container env
        for line in status.splitlines():
            if line.startswith("Name:") and ("proot" in line.lower()):
                info.is_proot_distro = True
    except Exception:
        pass
    # 常见 proot-distro 标识符
    release_file = Path("/etc/os-release")
    if release_file.is_file():
        try:
            content = release_file.read_text(errors="ignore")
            if "ubuntu" in content.lower():
                info.proot_distro_name = "ubuntu"
            elif "debian" in content.lower():
                info.proot_distro_name = "debian"
            elif "alpine" in content.lower():
                info.proot_distro_name = "alpine"
            elif "arch" in content.lower():
                info.proot_distro_name = "arch"
        except Exception:
            pass


def _detect_zerotermux_version(info: PlatformInfo) -> None:
    # 优先环境变量
    for env_key in ("ZEROTERMUXTARGET_VERSION", "ZEROTERMUXTARGET_VER",
                    "ZERO_TERMUXTARGET_VERSION", "ZERO_TERMUXTARGET_VER"):
        val = os.environ.get(env_key)
        if val:
            info.zerotermux_version = val
            return
    # 其次从 packages.xml 路径读取（需 root，一般读不到，仅尝试）
    package_db_candidates = [
        "/data/system/packages.xml",
    ]
    for db in package_db_candidates:
        try:
            content = Path(db).read_text(errors="ignore")
            if "com.zerotermux" in content:
                # 简单正则尝试提取 versionName
                import re
                m = re.search(
                    r'name="com\.zerotermux"[^>]*versionName="([^"]+)"',
                    content,
                )
                if m:
                    info.zerotermux_version = m.group(1)
                    return
        except Exception:
            continue


def _detect_memory_mb() -> int:
    try:
        meminfo = Path("/proc/meminfo").read_text(errors="ignore")
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    kb = int(parts[1])
                    return kb // 1024
    except Exception:
        pass
    return 0


def _compute_recommendations(info: PlatformInfo) -> None:
    # headless 推荐：无 DISPLAY、Android、Termux、proot（无 X server）默认 headless=true
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    info.has_display = has_display
    info.recommended_headless = not has_display

    # 移动端/Android 推荐参数
    args = []
    if info.needs_mobile_optimized_browser:
        # 已默认带 --no-sandbox --disable-gpu --disable-dev-shm-usage
        # 增加内存受限、无 GPU 硬件加速的降级参数
        args.extend([
            "--disable-software-rasterizer",
            "--use-gl=swiftshader-webgl",
            "--disable-vulkan",
            "--disable-skia-runtime-opensles",
            "--disable-features=AudioServiceOutOfProcess",
            "--mute-audio",
            "--disable-extensions",
            "--disable-default-apps",
            "--disable-sync",
            "--no-first-run",
        ])
        # 小内存设备（< 4GB）进一步限制
        if 0 < info.memory_total_mb < 4096:
            args.extend([
                "--memory-pressure-off",
                "--renderer-process-limit=1",
                "--in-process-gpu",
            ])
    info.recommended_extra_browser_args = tuple(args)


def detect_platform() -> PlatformInfo:
    info = PlatformInfo()
    arch = _detect_arch()
    info.arch = arch
    info.termux_prefix = _detect_termux_prefix()
    info.termux_home = _detect_termux_home()
    _detect_is_android(info, arch)
    _detect_is_termux(info)
    _detect_is_proot(info)
    _detect_zerotermux_version(info)
    info.memory_total_mb = _detect_memory_mb()
    _compute_recommendations(info)
    return info


# 全局单例，懒加载
_platform_info_singleton: Optional[PlatformInfo] = None


def get_platform_info(force_refresh: bool = False) -> PlatformInfo:
    global _platform_info_singleton
    if _platform_info_singleton is None or force_refresh:
        _platform_info_singleton = detect_platform()
    return _platform_info_singleton
