from playwright.sync_api import sync_playwright, Page, Browser
import os
import sys
import time
from typing import Dict, Any, Set, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from .config_manager import config_manager
from utils.cookie_loader import load_firefox_cookies
from utils.har_loader import find_har_file, load_api_pattern_from_har, print_har_instructions
from utils.platform_detector import get_platform_info


# ZeroTermux / Termux / proot-distro 环境中 Playwright 定位 Chromium 的特殊路径
# Termux 上一般通过 proot-distro 安装的 Ubuntu/Debian 里装 chromium-browser / chromium，
# 或直接使用 Termux 自己的 chromium 包（在 $PREFIX/bin/chromium）
EXTRA_CHROMIUM_SEARCH_PATHS: Tuple[str, ...] = (
    # Termux proot-distro: ubuntu
    "/data/data/com.zerotermux/files/home/.proot-distro/ubuntu/usr/bin/chromium",
    "/data/data/com.zerotermux/files/home/.proot-distro/ubuntu/usr/bin/chromium-browser",
    "/data/data/com.termux/files/home/.proot-distro/ubuntu/usr/bin/chromium",
    "/data/data/com.termux/files/home/.proot-distro/ubuntu/usr/bin/chromium-browser",
    # Termux proot-distro: debian
    "/data/data/com.zerotermux/files/home/.proot-distro/debian/usr/bin/chromium",
    "/data/data/com.zerotermux/files/home/.proot-distro/debian/usr/bin/chromium-browser",
    "/data/data/com.termux/files/home/.proot-distro/debian/usr/bin/chromium",
    "/data/data/com.termux/files/home/.proot-distro/debian/usr/bin/chromium-browser",
    # Termux 原生 chromium 包
    "/data/data/com.zerotermux/files/usr/bin/chromium",
    "/data/data/com.termux/files/usr/bin/chromium",
    # 通用 linux 发行版
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium",
    # macOS
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def _locate_chromium_executable() -> Optional[str]:
    """在 ZeroTermux/Termux/Linux 上定位可用的 Chromium。
    优先使用环境变量 MIHOYO_TOOLKIT_CHROMIUM_BIN 强制覆盖。"""
    env_override = os.environ.get("MIHOYO_TOOLKIT_CHROMIUM_BIN")
    if env_override and os.path.isfile(env_override) and os.access(env_override, os.X_OK):
        return env_override
    for p in EXTRA_CHROMIUM_SEARCH_PATHS:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


@dataclass
class ScraperConfig:
    url: str
    output_filename: str
    headless: bool = False
    wait_seconds: int = 3
    timeout: int = 120000
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    browser_args: list = None
    scroll_delay: float = 2.0
    incremental_mode: bool = False
    existing_urls: Set[str] = None
    # API拦截配置
    scraper_name: str = ""               # 抓取器名称，用于HAR文件目录
    api_url_keywords: list = field(default_factory=list)  # API URL匹配关键词
    api_domain_filter: str = ""           # Cookie域名过滤
    use_firefox_cookies: bool = False     # 是否加载Firefox Cookie
    # ZeroTermux 专属（运行时由基类自动注入）
    custom_chromium_executable: Optional[str] = None


class BaseScraper:
    """基础抓取器类，提供通用的网页抓取功能
    针对 ZeroTermux / Termux（Android）额外处理：
    1. 无显示环境下 headless=false 自动回退为 true，避免 DISPLAY 崩溃报错
    2. 自动检测 Termux/proot 下可用的 chromium/chromium-browser 可执行路径，
       传入 executable_path，绕开 playwright install chromium 在 ARM 下的下载失败
    3. 注入禁用音频 OOP、软件 GL、--single-process 等移动端稳定参数
    """

    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self.platform_info = get_platform_info()

        # 移动端/终端化无图形环境保护：强制 headless
        if not self.config.headless and not self.platform_info.has_display:
            print("[WARN] 当前环境无可用显示服务器（DISPLAY/WAYLAND_DISPLAY 未设置），自动切换到 headless=true")
            self.config.headless = True

        # 基础 browser_args
        if self.config.browser_args is None:
            self.config.browser_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]

        # 在 ZeroTermux / Termux / Android 上追加稳定化参数（与 config_manager 的覆盖层一致）
        if self.platform_info.needs_mobile_optimized_browser:
            extra_args = list(self.platform_info.recommended_extra_browser_args)
            for arg in extra_args:
                if arg not in self.config.browser_args:
                    self.config.browser_args.append(arg)
            # ARM 环境下常用的规避崩溃参数
            for arg in (
                "--disable-web-security",
                "--allow-running-insecure-content",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ):
                if arg not in self.config.browser_args:
                    self.config.browser_args.append(arg)
            # <4GB 内存的低内存模式
            if 0 < self.platform_info.memory_total_mb < 4096:
                for arg in (
                    "--memory-pressure-off",
                    "--renderer-process-limit=1",
                    "--in-process-gpu",
                ):
                    if arg not in self.config.browser_args:
                        self.config.browser_args.append(arg)

        # 自定义 chromium 可执行路径（Termux / proot 下找不到 playwright 打包二进制时使用）
        if not self.config.custom_chromium_executable:
            self.config.custom_chromium_executable = _locate_chromium_executable()

        self.html_dir = config_manager.get_output_dir("html")
        self.save_path = os.path.join(self.html_dir, self.config.output_filename)

        # 增量模式下初始化已存在URL集合
        if self.config.incremental_mode and self.config.existing_urls is None:
            self.config.existing_urls = set()

        # 用于检测新URL的选择器模板（子类可覆盖）
        self.url_selector_template = "a[href*='/article/'], a[href*='/news/']"

        # API拦截状态
        self._api_data = []
        self._api_stop_requested = False

    def _setup_browser(self, playwright) -> tuple[Browser, Page]:
        """配置并启动浏览器，子类可覆盖以加载Cookie"""
        browser_args = self.config.browser_args.copy() if self.config.browser_args else []
        if not self.config.headless:
            browser_args.extend(["--start-maximized"])

        launch_kwargs: Dict[str, Any] = {
            "headless": self.config.headless,
            "args": browser_args,
        }

        if self.config.custom_chromium_executable:
            launch_kwargs["executable_path"] = self.config.custom_chromium_executable
            print(f"[INFO] 使用自定义 Chromium 路径: {self.config.custom_chromium_executable}")

        try:
            browser = playwright.chromium.launch(**launch_kwargs)
        except Exception as exc:
            # 典型错误 1：aarch64 上 Playwright 未下载 chromium；典型错误 2：缺少依赖库
            # 给用户打印更友好的诊断信息
            if self.platform_info.needs_mobile_optimized_browser:
                print("[ERROR] Playwright 无法启动浏览器（ZeroTermux/Termux 环境）。请先执行 scripts/install_zerotermux.sh，或设置环境变量：")
                print("        export MIHOYO_TOOLKIT_CHROMIUM_BIN=/path/to/chromium")
                print("        参考 README_ZEROTERMUX.md 第 2 节（proot-distro 推荐方案）")
            raise exc

        context_kwargs: Dict[str, Any] = {
            "user_agent": self.config.user_agent,
            "no_viewport": True,
        }
        # Android/移动端 UA 下设置一个合理的移动端 viewport 作为 fallback（no_viewport=True 会覆盖，但给上下文默认）
        if self.platform_info.needs_mobile_optimized_browser and "Mobile" in str(self.config.user_agent):
            context_kwargs["viewport"] = {"width": 390, "height": 844}
            context_kwargs["device_scale_factor"] = 3
            context_kwargs["is_mobile"] = True
            context_kwargs["has_touch"] = True

        context = browser.new_context(**context_kwargs)

        if self.config.use_firefox_cookies and self.config.api_domain_filter:
            cookies = load_firefox_cookies(domain_filter=self.config.api_domain_filter)
            if cookies:
                try:
                    context.add_cookies(cookies)
                    print(f"[INFO] 已加载 {len(cookies)} 条 Firefox Cookie ({self.config.api_domain_filter})")
                except Exception as e:
                    print(f"[WARN] 加载 Cookie 失败: {e}")

        page = context.new_page()

        if not self.config.headless:
            print("[INFO] 浏览器窗口将以最大化模式打开")

        return browser, page

    def _setup_api_interception(self, page: Page, on_data_callback: Callable = None):
        """设置API响应拦截，子类调用此方法启用自动检测

        on_data_callback: 收到数据时的回调函数 (data: dict) -> list
        """
        self._api_data = []
        self._api_stop_requested = False
        keywords = self.config.api_url_keywords
        incremental_enabled = self.config.incremental_mode and self.config.existing_urls
        stop_on_existing = config_manager.get("incremental_settings.stop_on_existing", True)

        def handle_response(response):
            if not response.ok:
                return

            url = response.url
            if keywords and not any(kw in url for kw in keywords):
                return

            try:
                data = response.json()
            except Exception:
                return

            items = []
            if on_data_callback:
                items = on_data_callback(data)
            else:
                items = self._extract_items_from_api(data)

            if items:
                self._api_data.extend(items)
                print(f"[INFO] 拦截到API响应: +{len(items)} 条 (共 {len(self._api_data)} 条)")

                if incremental_enabled and stop_on_existing:
                    for item in items:
                        item_url = item.get("url", "")
                        if item_url and item_url in self.config.existing_urls:
                            print(f"[INFO] 发现已存在数据，增量模式停止")
                            self._api_stop_requested = True
                            return

        page.on('response', handle_response)

    def _extract_items_from_api(self, data: dict) -> list:
        """从API响应中提取数据项，子类可覆盖"""
        return []

    def _build_html_from_api_data(self, items: list) -> str:
        """将API数据构建为HTML，子类必须覆盖（如果使用API拦截）"""
        return ""

    def _check_api_data_or_har(self) -> Optional[str]:
        """检查API数据是否收集成功，失败则尝试HAR回退

        返回: HAR回退的HTML内容，或None表示需要提示用户
        """
        if self._api_data:
            return None  # API数据收集成功，无需HAR

        print("\n[WARN] 自动检测API未获取到数据")

        if self.config.scraper_name:
            har_path = find_har_file(self.config.scraper_name)
            if har_path:
                print(f"[INFO] 检测到HAR文件: {har_path}")
                return "use_har"  # 标记需要用HAR重试

            # 没有HAR文件，打印指引
            domain_keywords = self.config.api_domain_filter.split(',') if self.config.api_domain_filter else None
            print_har_instructions(
                self.config.scraper_name,
                self.config.url,
                domain_keywords
            )
            return None

        return None

    def _scroll_to_bottom(self, page: Page) -> None:
        """滚动页面到底部以加载更多内容，增量模式下检测已存在URL并提前停止"""
        last_height = page.evaluate("document.body.scrollHeight")
        attempts = 0
        incremental_enabled = self.config.incremental_mode and self.config.existing_urls
        stop_on_existing = config_manager.get("incremental_settings.stop_on_existing", True)

        if incremental_enabled:
            print(f"[INFO] 增量模式已启用，已存在 {len(self.config.existing_urls)} 条数据")

        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(self.config.scroll_delay)
            new_height = page.evaluate("document.body.scrollHeight")

            # 增量模式：检测当前页面URL是否已存在
            if incremental_enabled:
                found_existing = self._check_existing_urls(page)
                if found_existing and stop_on_existing:
                    print("[INFO] 发现已存在数据，增量模式停止滚动")
                    break

            if new_height == last_height:
                attempts += 1
                if attempts >= 3:
                    print("[INFO] 页面高度不再变化，停止滚动")
                    break
            else:
                attempts = 0

            last_height = new_height

    def _check_existing_urls(self, page: Page) -> bool:
        """检查当前页面是否包含已存在的URL"""
        try:
            # 获取当前页面所有URL
            current_urls = page.evaluate(f"""
                Array.from(document.querySelectorAll('{self.url_selector_template}'))
                    .map(el => el.href)
                    .filter(url => url && url.includes('/article/') || url.includes('/news/'))
            """)

            # 检查是否有已存在的URL
            for url in current_urls:
                if url in self.config.existing_urls:
                    print(f"[INFO] 检测到已存在URL: {url}")
                    return True

            return False

        except Exception as e:
            print(f"[WARN] URL检测失败: {e}")
            return False

    def _process_page(self, page: Page) -> str:
        """处理页面并返回HTML内容"""
        page.goto(self.config.url, timeout=self.config.timeout)
        page.wait_for_load_state("networkidle")
        time.sleep(self.config.wait_seconds)
        
        self._scroll_to_bottom(page)
        
        return page.content()
    
    def run(self) -> str:
        """执行主抓取流程"""
        print(f"\n【启动】抓取页面: {self.config.url}")
        
        with sync_playwright() as p:
            browser, page = self._setup_browser(p)
            try:
                html_content = self._process_page(page)
            finally:
                browser.close()
        
        self._save_html(html_content)
        return html_content
    
    def _save_html(self, html_content: str) -> None:
        """保存HTML内容到文件"""
        with open(self.save_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ 完成：{self.save_path}")
    
    def extract_data(self, html_content: str) -> Any:
        """提取数据（子类必须实现）"""
        raise NotImplementedError("子类必须实现 extract_data 方法")
