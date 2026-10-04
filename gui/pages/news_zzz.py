"""绝区零新闻页面"""

from gui.pages.news_page import NewsPage


class ZZZNewsPage(NewsPage):
    game_key = "zzz"
    game_name = "绝区零"

    def _get_func(self, action: str, incremental: bool):
        if action == "fetch":
            from fetchers import run_news_zzz
            return lambda: run_news_zzz(incremental=incremental)
        else:
            from extractors import run_extract_news_zzz
            return lambda: run_extract_news_zzz(incremental=incremental)
