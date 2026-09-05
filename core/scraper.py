from playwright.sync_api import sync_playwright, Page, Browser
import os
import time
from typing import Dict, Any, Set, Optional, List, Callable
from dataclasses import dataclass, field
from .config_manager import config_manager
from utils.cookie_loader import load_firefox_cookies
from utils.har_loader import find_har_file, load_api_pattern_from_har, print_har_instructions


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


class BaseScraper:
    """基础抓取器类，提供通用的网页抓取功能"""

    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        if self.config.browser_args is None:
            self.config.browser_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]

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

        browser = playwright.chromium.launch(
            headless=self.config.headless,
            args=browser_args
        )

        context = browser.new_context(
            user_agent=self.config.user_agent,
            no_viewport=True
        )

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
        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
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
