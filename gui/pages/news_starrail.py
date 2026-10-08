"""星穹铁道新闻页面"""

from gui.pages.news_page import NewsPage


class StarRailNewsPage(NewsPage):
    game_key = "starrail"
    game_name = "星穹铁道"

    def _get_func(self, action: str, incremental: bool):
        if action == "fetch":
            from fetchers import run_news_starrail
            return lambda: run_news_starrail(incremental=incremental)
        else:
            from extractors import run_extract_news_starrail
            return lambda: run_extract_news_starrail(incremental=incremental)
