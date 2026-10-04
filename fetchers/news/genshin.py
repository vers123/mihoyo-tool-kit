"""
原神新闻抓取器
基于 content_v2_user 统一 API 架构（iChanId=719，共 4637 条）
"""

from .base import GameNewsBaseScraper
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry


class GenshinNewsScraper(GameNewsBaseScraper):
    """原神新闻抓取器"""

    game_key = "genshin"

    def __init__(self, incremental: bool = False):
        super().__init__(incremental=incremental)

        # 原神特有的 DOM 选择器（兜底用）
        self.dom_item_selector = 'li.news__item'
        self.load_more_selector = 'li.news__more, li.recommend__more'
        self.url_selector_template = "a[href*='/main/news/detail/']"

    def _get_existing_urls(self) -> set:
        """增量模式下使用 GenshinNewsExtractor 加载已有数据"""
        try:
            from extractors.news.genshin import GenshinNewsExtractor
            extractor = GenshinNewsExtractor()
            return extractor.get_existing_urls()
        except Exception:
            return super()._get_existing_urls()


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(incremental: bool = False):
    """运行原神新闻抓取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}抓取原神新闻页面")

    scraper = GenshinNewsScraper(incremental=incremental)
    html_content = scraper.run()

    if html_content:
        print("[OK] 原神新闻页面抓取完成")
        return html_content
    else:
        print("[ERROR] 原神新闻页面抓取失败")
        return None


if __name__ == "__main__":
    run()
