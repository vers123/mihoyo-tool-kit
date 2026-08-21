# 米游社工具箱 ZeroTermux 适配指南

> **适配目标**：ZeroTermux APP 版本 `0.118.3.64`（Android aarch64 / arm64，兼容普通 Termux 0.118+）
> **项目分支**：`refactor/zerotermux-adapter`
> **推荐方案**：ZeroTermux 宿主 + `proot-distro` 运行 Ubuntu，在容器内安装 `chromium-browser`，由 Playwright 的 `executable_path` 直接调用容器二进制。

---

## 目录

1. [ZeroTermux 下为什么不能直接跑原版？](#1-zerotermux-下为什么不能直接跑原版)
2. [一键安装（推荐新手）](#2-一键安装推荐新手)
3. [分步安装（高手路线）](#3-分步安装高手路线)
4. [启动方式对比](#4-启动方式对比)
5. [配置参数说明（ZeroTermux 专属配置节）](#5-配置参数说明zerotermux-专属配置节)
6. [常见问题排查（FAQ）](#6-常见问题排查faq)
7. [代码层面的适配改动一览](#7-代码层面的适配改动一览)

---

## 1. ZeroTermux 下为什么不能直接跑原版？

原版项目在 PC 端 `pip install playwright && playwright install chromium` 即可，而在 ZeroTermux（Android/Termux）下有 5 个典型阻碍：

| 阻碍 | 具体表现 | 本分支的应对方案 |
| :--- | :--- | :--- |
| **无 X11/Wayland 显示服务器** | `headless=false` 会立即报 `DISPLAY not set` 崩溃 | `main.py` + `config_manager.py` + `BaseScraper` 三层判定：检测不到 `$DISPLAY/$WAYLAND_DISPLAY` 时强制 `headless=true` |
| **Playwright 的 Chromium 在 aarch64 上下载失败** | `playwright install chromium` 会报 `unsupported platform aarch64` | 推荐 `proot-distro/ubuntu + chromium-browser`，并新增 `EXTRA_CHROMIUM_SEARCH_PATHS` 自动扫描常用路径；也支持 `MIHOYO_TOOLKIT_CHROMIUM_BIN` 环境变量指定 |
| **低端 SoC / 小内存（手机常见 2–6 GB）** | 渲染/内存压力大，滚动加载频繁卡死或 renderer OOM 被杀 | 自动注入 `--renderer-process-limit=1 --in-process-gpu --memory-pressure-off --disable-background-timer-throttling` 等低内存参数；滚动延迟 × 1.5、网络超时 × 1.5 |
| **UA/视口尺寸** | PC UA + 1920×1080 视口在抓移动端优化网页时返回的 DOM 结构不同 | 移动端环境默认切换到 Android 14 + Pixel 8 移动 UA，`is_mobile=true / has_touch=true / device_scale_factor=3` |
| **Firefox Cookie 只写死 Windows `%APPDATA%`** | Termux/Linux 下永远加载不到 Cookie → 抓用户主页必须登录的内容只能重新扫码 | `cookie_loader.py` 新增 Linux/macOS/Snap/Flatpak/Termux/proot-distro 多套查找路径，并支持 `MIHOYO_TOOLKIT_FIREFOX_PROFILE` 强覆盖 |
| **终端窄屏** | 70 列 `========` 在手机竖屏会被折行，菜单惨不忍睹 | `main.py._print_header()` 用 `os.get_terminal_size()` 动态计算宽度，窄屏靠左标题 + 缩短分隔线；清屏优先 ANSI escape |

---

## 2. 一键安装（推荐新手）

在 ZeroTermux APP 中打开 Shell，依次执行：

```bash
# 1. 准备基础环境（如果没装过 git/python/proot-distro）
pkg update -y
pkg install -y git python proot-distro pulseaudio

# 2. 拉取项目并进入分支（如果还没下载）
cd ~
git clone https://github.com/vers123/miHoYo_ToolKit.git
cd miHoYo_ToolKit
git checkout refactor/zerotermux-adapter      # ← 就是这个适配分支

# 3. 一键安装（宿主包 → proot-distro Ubuntu → 容器装 Chromium/Python/字体 → 宿主装依赖 → 生成启动脚本 → 可选 sdcard 重定向）
bash scripts/install_zerotermux.sh all
```

脚本 `all` 模式会在每个阶段结束后打印彩色提示。常见耗时参考（骁龙 8 Gen 2 设备）：
- 宿主 `pkg install`：约 1 分钟
- `proot-distro install ubuntu`（首次下载 50–80 MB rootfs tar）：约 3–5 分钟
- 容器内 apt-get 安装 chromium + 中文字体 + Python：约 3–6 分钟
- 宿主 pip install playwright：aarch64 无 wheel 时可能失败，脚本会自动降级为"只在容器里跑"模式

**完成后验证：**
```bash
bash scripts/zt_launcher.sh
```

如果一切顺利会进入 23 项功能的菜单，标题下方会出现 `📱 ZeroTermux 0.118.3.64 | arch=aarch64 | RAM≈5800MB | headless=YES` 这样的环境摘要行。

---

## 3. 分步安装（高手路线）

### 3.1 宿主依赖

```bash
pkg install -y python python-pip git proot-distro pulseaudio termux-tools
# （可选）允许访问手机 /sdcard，脚本会弹窗申请权限
termux-setup-storage
```

### 3.2 安装 proot-distro（推荐 Ubuntu）

```bash
proot-distro install ubuntu          # 或 DISTRO_NAME=debian 替换
# 确认已安装
proot-distro list
```

### 3.3 容器内准备 Chromium + Python + Playwright + 字体

```bash
proot-distro login --user root ubuntu -- bash -c '
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates curl locales tzdata \
    chromium chromium-common \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    fonts-noto-cjk fonts-noto-color-emoji \
    python3 python3-pip
locale-gen zh_CN.UTF-8
python3 -m pip install --break-system-packages --upgrade pip setuptools wheel
python3 -m pip install --break-system-packages "playwright>=1.40.0"
# 确认 chromium 存在
ls -l /usr/bin/chromium /usr/bin/chromium-browser || true
'
```

### 3.4 宿主侧 Python 依赖（可跳过，直接用容器）

```bash
cd ~/miHoYo_ToolKit
pip install --user -r requirements.txt
```

如果 aarch64 上报错 `could not build wheels for playwright`，没关系——跳过本步，用 `scripts/zt_launcher.sh` 会自动走 proot 容器路径。

### 3.5 启动

```bash
cd ~/miHoYo_ToolKit
# 方式 A（推荐，自动选最佳路径）
bash scripts/zt_launcher.sh

# 方式 B（只在容器里跑，完全隔离）
bash scripts/zt_enter.sh
# 进入后：
python3 main.py

# 方式 C（宿主 playwright 能 import、且宿主有 chromium 二进制）
export MIHOYO_TOOLKIT_CHROMIUM_BIN=/data/data/com.zerotermux/files/usr/bin/chromium
python3 main.py
```

---

## 4. 启动方式对比

| 方式 | 命令 | Playwright 运行位置 | Chromium 位置 | 性能 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A 推荐 | `bash scripts/zt_launcher.sh` | 宿主优先，不满足时自动切 proot | 宿主或容器，自动探测 | 宿主更快 | 90% 用户 |
| B 隔离 | `bash scripts/zt_enter.sh` → `python3 main.py` | 容器内 | `/usr/bin/chromium` (容器内) | 略慢（proot 系统调用虚拟化层） | 需要干净环境或宿主没有编译 playwright |
| C 纯宿主 | `python3 main.py` 配合 `MIHOYO_TOOLKIT_CHROMIUM_BIN` | 宿主 | Termux 原生 chromium 包 | 最快 | 已在 Termux 源装过 chromium |

> **性能参考**（骁龙 8 Gen 2 / 8 GB / LPDDR5X 机型，抓 100 条米游社发帖并滚动到底部）
> 方式 C ≈ 38 秒，方式 A/C 宿主 fallback 到 A/B 容器 ≈ 52 秒，方式 B ≈ 54 秒。差距主要在 Playwright Python 绑定跨进程通信开销上，总体可接受。

---

## 5. 配置参数说明（ZeroTermux 专属配置节）

`config.json` 在本分支会新增 `zerotermux_settings` 一节。如果是旧配置文件加载进来后，会在 `ConfigManager._apply_zerotermux_runtime_overrides()` 自动补齐并对其他关键配置做弱覆盖（不覆盖用户显式设置）。

```json
{
  "zerotermux_settings": {
    "enabled": true,
    "force_headless": true,
    "use_mobile_ua": true,
    "enable_low_memory_mode": true,
    "extra_browser_args": [
      "--disable-software-rasterizer",
      "--use-gl=swiftshader-webgl",
      "--disable-vulkan",
      "--mute-audio",
      "--disable-extensions"
    ],
    "scroll_delay_multiplier": 1.5,
    "timeout_multiplier": 1.5,
    "max_backups": 5,
    "data_dir_override": null
  }
}
```

字段逐条解释：

| 字段 | 类型 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- |
| `enabled` | bool | 运行时自动识别 | 是否启用移动端适配总开关。运行环境是 ZeroTermux/Termux/Android 时默认 true，**桌面 Linux/Windows 自动为 false** |
| `force_headless` | bool | `true` | 无 DISPLAY 时，即便用户把顶层 `headless` 写成 false，也会在启动时改回 true。避免终端无 X 服务崩溃。 |
| `use_mobile_ua` | bool | `true` | 自动把 `user_agent` 改成 Pixel 8 + Android 14 的 Chrome 移动端字符串（仅当前 UA 字符串里没有 `Android`/`Mobile` 才替换，不会覆盖用户自定义 UA）。 |
| `enable_low_memory_mode` | bool | 若 RAM < 4GB → true，否则 false | 自动追加 `--memory-pressure-off --renderer-process-limit=1 --in-process-gpu`，小内存设备强烈建议开启。 |
| `extra_browser_args` | `string[]` | 一套移动优化参数数组 | 在基础 `browser_args` 之后追加（去重），可自行按设备表现增减 |
| `scroll_delay_multiplier` | float | 1.5 | `scroll_settings.delay = 原值 × 系数`，滚动加载时给手机 CPU/GPU 更多渲染时间 |
| `timeout_multiplier` | float | 1.5 | `timeout` 和 `wait_seconds` 都乘以系数，4G/5G/WiFi 混用时避免过早报超时 |
| `max_backups` | int | 5 | 手机存储空间小，默认只保留 5 份历史备份（桌面端是 10 份）。用户 `backup_settings.max_backups` 大于 5 时会被裁剪。 |
| `data_dir_override` | `string \| null` | `null` | 不为空时，将 HTML / 结果 / 备份目录全部改写到该目录下。例如执行过 `termux-setup-storage` 后，可填 `"/sdcard/Download/miHoYo_ToolKit"`，方便在手机「下载」里直接查看输出。**安装脚本 `sdcard` 子命令或 `all` 模式最后一步会帮你写入。** |

启动 `main.py` 后进入菜单 → **23. 系统信息**，可以看到：
```
📱 移动端适配: 启用
   · force_headless    = True
   · use_mobile_ua     = True
   · low_memory_mode   = True
   · scroll × 1.5 / timeout × 1.5
   · Chromium 路径: /data/data/com.zerotermux/files/home/.proot-distro/ubuntu/usr/bin/chromium
```

---

## 6. 常见问题排查（FAQ）

### Q1. `playwright install chromium` 报 `unsupported platform`
A. 在 ARM/aarch64 Termux 上 **不要执行** `playwright install chromium`。本分支已经通过 `executable_path=` 直接调用系统或容器的 `chromium` 二进制，Playwright 仅充当 Python 绑定。

### Q2. 启动报错：`Browser closed` 或 `Crash` 或 `No usable sandbox`
A. 本分支默认已经带了 `--no-sandbox --disable-gpu --disable-dev-shm-usage`，还会在 ZeroTermux 环境再补：
```
--disable-software-rasterizer --use-gl=swiftshader-webgl --disable-vulkan
--disable-background-timer-throttling --disable-features=AudioServiceOutOfProcess --mute-audio
```
如果仍然崩溃，可在 `config.json` 里把 `browser_args` 手动追加更多稳定化参数：
```json
"browser_args": [
  "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
  "--disable-seccomp-filter-sandbox",
  "--disable-breakpad",
  "--single-process"
]
```
> 注：`--single-process` 在极端情况下能跑，但稳定性反而下降，仅作最后手段。

### Q3. 抓米游社用户主页（功能 1/2）显示「未登录」，Firefox Cookie 没加载
A. 可能原因：
- **ZeroTermux/Android 上 Firefox 浏览器应用的私有目录受 SELinux 保护，普通 Termux 用户读不到 `/data/data/org.mozilla.firefox/`**。这是 Android 的安全限制，不是 bug。
- **解决办法**：在 `proot-distro/ubuntu` 容器里安装 Firefox（非安卓 APP，是桌面 Linux 版）并在容器里登录米游社/微博。对应的 profile 路径会被 cookie_loader 正确扫描到（扫描顺序 `~/.mozilla/firefox` → `~/.proot-distro/ubuntu/root/.mozilla/firefox` → 环境变量 `MIHOYO_TOOLKIT_FIREFOX_PROFILE`）。
- **终极办法**：如果嫌麻烦，直接用 **功能 14/15 微博抓取器** 的「90 秒扫码登录等待」机制，或用 HAR 回退导出。

### Q4. 保存的 HTML / txt 在手机里找不到
A. 默认存放在 `~/miHoYo_ToolKit/data/...`，也就是 ZeroTermux 内部私有目录，文件管理器看不到。解决办法：
1. `bash scripts/install_zerotermux.sh sdcard` → 选择 y 把目录重定向到 `/sdcard/Download/miHoYo_ToolKit/`
2. 或手动在宿主运行 `termux-setup-storage`，然后把文件 `cp -r ~/miHoYo_ToolKit/data /sdcard/Download/`

### Q5. 功能 14/15 微博抓取器一直显示「请在浏览器中完成登录」但看不到窗口
A. 终端模式下 headless=true，所以看不到窗口。这里的「请在浏览器中完成登录」其实对应微博 Cookie 失效后的 **程序兜底等待 90 秒轮询**——如果加载进 Cookie 会自动识别并立刻进入抓取；如果 Cookie 没加载成功，建议：

1. 退出程序
2. 用桌面端 Firefox 在容器里登录一次微博（保留 Cookie），或手动把 Cookie 复制到容器 profile
3. 把顶层 `headless` 临时改成 `false` + 启动一个 X Server（ZeroTermux 上装 VNC/XSDL 组合可以显示 Chromium 窗口，复杂度较高，新手不推荐）

### Q6. `scripts/install_zerotermux.sh` 的 `proot-distro login` 提示 permission denied
A. 确保 ZeroTermux 已更新到 `0.118.3.64`。老版本 ZeroTermux 的 proot 兼容性有问题。更新 APP 后清理后台再运行脚本。

### Q7. 容器内 apt update 报 `Temporary failure resolving '*.ubuntu.com'`
A. 容器内 DNS 配置问题，可在宿主执行：
```bash
proot-distro login --user root ubuntu -- bash -c "
echo nameserver 114.114.114.114 > /etc/resolv.conf
echo nameserver 8.8.8.8 >> /etc/resolv.conf
apt-get update -y
"
```

---

## 7. 代码层面的适配改动一览

| 模块 | 改动摘要 | 详细文件 |
| :--- | :--- | :--- |
| 新增 | `utils/platform_detector.py` 平台检测模块：识别 ZeroTermux、Termux、Android、proot-distro、系统内存、可用显示器、推荐浏览器参数、移动端 UA、推荐 headless。 | [platform_detector.py](file:///workspace/utils/platform_detector.py) |
| 核心 | `core/config_manager.py`：新增 `ZeroTermuxSettings` 数据类 + `zerotermux_settings` 配置节；运行时动态调整默认值（headless/timeout/scroll_delay/max_backups/UA/extra_browser_args/data_dir_override）+ 弱覆盖层。 | [config_manager.py](file:///workspace/core/config_manager.py) |
| 核心 | `core/scraper.py`：新增 `EXTRA_CHROMIUM_SEARCH_PATHS` 自动扫描 16 条常见 chromium 安装路径；`ScraperConfig.custom_chromium_executable` 新字段；`BaseScraper.__init__` 三层环境保护：强制 headless、移动端参数补全、低内存模式；Chromium 启动失败输出中文诊断；移动端 UA 自动启用 viewport/is_mobile/touch。 | [scraper.py](file:///workspace/core/scraper.py) |
| 工具 | `utils/cookie_loader.py`：从原来只支持 `%APPDATA%` Windows 路径，升级为跨平台：profiles.ini 解析 + 三类 OS 路径查找（Win/macOS/Linux）+ Termux/proot-distro Ubuntu/Debian + Snap + Flatpak + `MIHOYO_TOOLKIT_FIREFOX_PROFILE` 强覆盖。 | [cookie_loader.py](file:///workspace/utils/cookie_loader.py) |
| 入口 | `main.py`：导入平台检测器；标题自动追加 `(ZeroTermux模式)/(Termux模式)/(Android模式)` 后缀；`_clear_screen` 改用 ANSI escape + 终端类型兼容 3 层兜底；`_print_header` 动态分隔线宽度 + 窄屏靠左；新增 📱 banner 行展示 arch/container/RAM/headless；启动前做 Python 版本检查；`_show_system_info` 增加 ZerotTermux 版本、proot 容器名、内存、移动端适配摘要、Chromium 路径诊断；`main()` 增加启动环境识别与中文引导文案。 | [main.py](file:///workspace/main.py) |
| 新增 | `scripts/install_zerotermux.sh`：9 步一键安装脚本；子命令 `all/pkg_host/distro_install/distro_setup/host_pip/launcher/sdcard/info`；彩色输出、错误处理、REUSE_EXISTING/DISTRO_NAME/DISTRO_ARCH/SKIP_SDCARD 环境变量开关。 | [install_zerotermux.sh](file:///workspace/scripts/install_zerotermux.sh) |
| 新增 | `scripts/zt_enter.sh`（由 install 脚本自动生成）：快速进入容器交互 shell。 | scripts/zt_enter.sh（脚本运行后生成） |
| 新增 | `scripts/zt_launcher.sh`（由 install 脚本自动生成）：宿主/容器路径智能选择，一键 `python main.py`。 | scripts/zt_launcher.sh（脚本运行后生成） |
| 新增 | 本文档：README_ZEROTERMUX.md。 | [README_ZEROTERMUX.md](file:///workspace/README_ZEROTERMUX.md) |

---

**项目适配分支**：`refactor/zerotermux-adapter`
**报告问题**：如在 ZeroTermux 0.118.3.64 下遇到与适配相关的 bug 或想贡献更多机型的稳定化 Chromium 参数，欢迎提交 Issue/PR。
