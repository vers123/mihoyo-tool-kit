"""原神新闻页面"""

from gui.pages.news_page import NewsPage


class GenshinNewsPage(NewsPage):
    game_key = "genshin"
    game_name = "原神"

    def _get_func(self, action: str, incremental: bool):
        if action == "fetch":
            from fetchers import run_news_genshin
            return lambda: run_news_genshin(incremental=incremental)
        else:
            from extractors import run_extract_news_genshin
            return lambda: run_extract_news_genshin(incremental=incremental)
