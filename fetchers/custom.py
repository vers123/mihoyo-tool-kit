import time
from playwright.sync_api import sync_playwright
from core.scraper import BaseScraper, ScraperConfig
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry


class CustomScraper(BaseScraper):
    def __init__(self, url: str, output_filename: str = "custom_page.html"):
        scraper_config = ScraperConfig(
            url=url,
            output_filename=output_filename,
            headless=config_manager.get("headless", False),
            wait_seconds=config_manager.get("wait_seconds", 3),
            timeout=config_manager.get("timeout", 120000),
            user_agent=config_manager.get("user_agent"),
            browser_args=config_manager.get("browser_args", []),
            scroll_delay=config_manager.get("scroll_settings.delay", 2.0)
        )
        super().__init__(scraper_config)

    def run(self):
        print(f"\n【启动】抓取自定义页面: {self.config.url}")

        with sync_playwright() as p:
            browser, page = self._setup_browser(p)
            try:
                page.goto(self.config.url, timeout=self.config.timeout)
                try:
                    page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                time.sleep(self.config.wait_seconds)

                self._scroll_to_bottom(page)

                html_content = page.content()
                self._save_html(html_content)

            finally:
                browser.close()

        return html_content


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(url: str = None, output_filename: str = "custom_page.html"):
    if not url:
        print("[ERROR] 请提供要抓取的URL")
        return None

    scraper = CustomScraper(url, output_filename)
    html_content = scraper.run()

    if html_content:
        print("[OK] 自定义页面抓取完成")
        return html_content
    else:
        print("[ERROR] 自定义页面抓取失败")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        filename = sys.argv[2] if len(sys.argv) > 2 else "custom_page.html"
        run(url, filename)
    else:
        print("使用方法: python custom.py <URL> [output_filename]")
        print("示例: python custom.py https://example.com my_page.html")
