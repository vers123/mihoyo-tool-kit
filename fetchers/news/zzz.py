"""
绝区零新闻抓取器
基于 content_v2_user 统一 API 架构（iChanId=273，共 1554 条）
"""

from .base import GameNewsBaseScraper
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry


class ZZZNewsScraper(GameNewsBaseScraper):
    """绝区零新闻抓取器"""

    game_key = "zzz"

    def __init__(self, incremental: bool = False):
        super().__init__(incremental=incremental)

        # 绝区零特有的 DOM 选择器（兜底用）
        self.dom_item_selector = 'div[class*="news-list__item"], li[class*="news-list__item"]'
        self.load_more_selector = 'button[class*="more"], div[class*="more"]'
        self.url_selector_template = "a[href*='/news/']"

    def _get_existing_urls(self) -> set:
        """增量模式下使用 ZZZNewsExtractor 加载已有数据"""
        try:
            from extractors.news.zzz import ZZZNewsExtractor
            extractor = ZZZNewsExtractor()
            return extractor.get_existing_urls()
        except Exception:
            return super()._get_existing_urls()


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(incremental: bool = False):
    """运行绝区零新闻抓取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}抓取绝区零新闻页面")

    scraper = ZZZNewsScraper(incremental=incremental)
    html_content = scraper.run()

    if html_content:
        print("[OK] 绝区零新闻页面抓取完成")
        return html_content
    else:
        print("[ERROR] 绝区零新闻页面抓取失败")
        return None


if __name__ == "__main__":
    run()
