"""
原神英文版新闻抓取器
基于 content_v2_user 统一 API 架构（iChanId=395，iAppId=32，共 2163 条）
API 域名：sg-public-api-static.hoyoverse.com
"""

from .base import GameNewsBaseScraper
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry


class GenshinENNewsScraper(GameNewsBaseScraper):
    """原神英文版新闻抓取器"""

    game_key = "genshin_en"

    def __init__(self, incremental: bool = False):
        super().__init__(incremental=incremental)

        self.dom_item_selector = 'li.news__item'
        self.load_more_selector = 'li.news__more, li.recommend__more'
        self.url_selector_template = "a[href*='/en/news/detail/']"

    def _get_existing_urls(self) -> set:
        try:
            from extractors.news.genshin_en import GenshinENNewsExtractor
            extractor = GenshinENNewsExtractor()
            return extractor.get_existing_urls()
        except Exception:
            return super()._get_existing_urls()


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(incremental: bool = False):
    """运行原神英文版新闻抓取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}抓取原神英文版新闻页面")

    scraper = GenshinENNewsScraper(incremental=incremental)
    html_content = scraper.run()

    if html_content:
        print("[OK] 原神英文版新闻页面抓取完成")
        return html_content
    else:
        print("[ERROR] 原神英文版新闻页面抓取失败")
        return None


if __name__ == "__main__":
    run()
