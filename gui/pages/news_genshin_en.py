"""原神英文版新闻页面"""

from gui.pages.news_page import NewsPage


class GenshinENNewsPage(NewsPage):
    game_key = "genshin_en"
    game_name = "原神(EN)"

    def _get_func(self, action: str, incremental: bool):
        if action == "fetch":
            from fetchers import run_news_genshin_en
            return lambda: run_news_genshin_en(incremental=incremental)
        else:
            from extractors import run_extract_news_genshin_en
            return lambda: run_extract_news_genshin_en(incremental=incremental)
