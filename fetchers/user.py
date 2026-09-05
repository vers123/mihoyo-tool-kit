import re
import time
import html
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser
from core.scraper import BaseScraper, ScraperConfig
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry
from utils.har_loader import find_har_file, print_har_instructions
from extractors.time import PostExtractor


class UserScraper(BaseScraper):
    """用户发帖抓取器 - 基于API响应拦截 + HAR回退"""

    def __init__(self, incremental: bool = False):
        existing_urls = None
        if incremental and config_manager.get("incremental_settings.enabled", True):
            extractor = PostExtractor()
            existing_urls = extractor.get_existing_urls()
            print(f"[INFO] 增量模式: 已存在 {len(existing_urls)} 条数据")

        scraper_config = ScraperConfig(
            url=config_manager.get("user_url"),
            output_filename="user_posts.html",
            headless=config_manager.get("headless", False),
            wait_seconds=config_manager.get("wait_seconds", 3),
            timeout=config_manager.get("timeout", 120000),
            user_agent=config_manager.get("user_agent"),
            browser_args=config_manager.get("browser_args", []),
            scroll_delay=config_manager.get("scroll_settings.delay", 2.0),
            incremental_mode=incremental,
            existing_urls=existing_urls,
            scraper_name="user",
            api_url_keywords=["userPostList", "postList"],
            api_domain_filter="miyoushe.com",
            use_firefox_cookies=config_manager.get("miyoushe_settings.use_firefox_cookies", True),
        )
        super().__init__(scraper_config)

        self.url_selector_template = "a[href*='/ys/article/']"

    def _extract_items_from_api(self, data: dict) -> list:
        """从API响应中提取帖子列表"""
        if not isinstance(data, dict):
            return []

        post_list = data.get("data", {}).get("list", [])
        items = []

        for post_item in post_list:
            post = post_item.get("post", post_item)
            post_id = post.get("post_id", "")
            subject = post.get("subject", "")
            created_at = post.get("created_at", 0)

            if not post_id:
                continue

            if isinstance(created_at, (int, float)) and created_at > 0:
                date_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d")
            else:
                date_str = str(created_at)

            items.append({
                "post_id": str(post_id),
                "subject": subject,
                "date": date_str,
                "url": f"https://www.miyoushe.com/ys/article/{post_id}"
            })

        return items

    def _build_html_from_api_data(self, items: list) -> str:
        """将API数据构建为HTML"""
        html_parts = ['<!DOCTYPE html><html lang="zh-cn"><head><meta charset="utf-8"><title>用户帖子</title></head><body>']

        for item in items:
            post_id = item.get("post_id", "")
            subject = item.get("subject", "")
            date_str = item.get("date", "")

            safe_title = html.escape(subject)
            safe_url = html.escape(f"/ys/article/{post_id}")
            safe_date = html.escape(date_str)

            html_parts.append(
                f'<div class="mhy-account-center-post-card">'
                f'<div>'
                f'<a href="{safe_url}">'
                f'<h3 class="mhy-article-card__h3">{safe_title}</h3>'
                f'</a>'
                f'<span class="mhy-account-center-time__small">{safe_date}</span>'
                f'</div>'
                f'</div>'
            )

        html_parts.append('</body></html>')
        return ''.join(html_parts)

    def _process_page(self, page: Page) -> str:
        """处理页面：自动拦截API → 失败则HAR回退"""
        self._setup_api_interception(page)

        page.goto(self.config.url, timeout=self.config.timeout)

        if self._api_stop_requested and self._api_data:
            print(f"\n[OK] 增量模式：已收集 {len(self._api_data)} 条新数据")
            return self._build_html_from_api_data(self._api_data)

        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass

        if self._api_stop_requested and self._api_data:
            print(f"\n[OK] 增量模式：已收集 {len(self._api_data)} 条新数据")
            return self._build_html_from_api_data(self._api_data)

        time.sleep(self.config.wait_seconds)

        self._scroll_for_data(page)

        if self._api_data:
            print(f"\n[OK] API拦截成功，共 {len(self._api_data)} 条帖子")
            return self._build_html_from_api_data(self._api_data)

        # API未获取到数据
        print("\n[WARN] 自动检测API未获取到数据")
        har_path = find_har_file(self.config.scraper_name)
        if har_path:
            print(f"[INFO] 检测到HAR文件: {har_path}")
            print("[INFO] 请删除HAR文件后重新运行，或手动检查API配置")
        else:
            print_har_instructions(
                self.config.scraper_name,
                self.config.url,
                ["bbs-api.miyoushe.com"]
            )

        print("[INFO] 回退到DOM抓取模式...")
        return page.content()

    def _scroll_for_data(self, page: Page) -> None:
        """滚动页面触发API请求"""
        scroll_delay = self.config.scroll_delay
        last_height = page.evaluate("document.body.scrollHeight")
        attempts = 0
        max_attempts = 5

        while not self._api_stop_requested:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(scroll_delay)
            new_height = page.evaluate("document.body.scrollHeight")

            if self._api_stop_requested:
                break

            if new_height == last_height:
                attempts += 1
                if attempts >= max_attempts:
                    print("[INFO] 页面高度不再变化，停止滚动")
                    break
            else:
                attempts = 0

            last_height = new_height


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(incremental: bool = False):
    """运行用户发帖抓取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}抓取用户发帖主页")

    scraper = UserScraper(incremental=incremental)
    html_content = scraper.run()

    if html_content:
        print("[OK] 用户发帖主页抓取完成")
        return html_content
    else:
        print("[ERROR] 用户发帖主页抓取失败")
        return None


if __name__ == "__main__":
    run()
