from .tutorial import TutorialExtractor, run as run_extract_tutorial
from .images import ImageExtractor, run as run_extract_images
from .time import PostExtractor, run as run_extract_time
from .weibo import WeiboExtractor, run as run_extract_weibo
from .excel_writer import export_to_excel, run as run_export_excel
from .txt_filter import (
    TxtFilter, run_filter,
    FIELD_ALL, FIELD_TITLE, FIELD_TITLE_INTRO, FIELD_TITLE_INTRO_CAT, FIELD_CHOICES,
    MATCH_EXACT, MATCH_FUZZY, MATCH_CHOICES,
)

# 新闻提取模块（新架构：子目录 + 基类 + 各游戏子类）
from .news import (
    GameNewsBaseExtractor,
    NewsItem,
    GenshinNewsExtractor,
    GenshinENNewsExtractor,
    ZZZNewsExtractor,
    SRNewsExtractor,
    run_extract_news_genshin,
    run_extract_news_genshin_en,
    run_extract_news_zzz,
    run_extract_news_starrail,
)

# 向后兼容：旧的 NewsExtractor / run_extract_news 指向原神新闻提取
NewsExtractor = GenshinNewsExtractor
run_extract_news = run_extract_news_genshin

__all__ = [
    "NewsExtractor",
    "TutorialExtractor",
    "ImageExtractor",
    "PostExtractor",
    "WeiboExtractor",
    "GameNewsBaseExtractor",
    "NewsItem",
    "GenshinNewsExtractor",
    "GenshinENNewsExtractor",
    "ZZZNewsExtractor",
    "SRNewsExtractor",
    "TxtFilter",
    "FIELD_ALL", "FIELD_TITLE", "FIELD_TITLE_INTRO", "FIELD_TITLE_INTRO_CAT", "FIELD_CHOICES",
    "MATCH_EXACT", "MATCH_FUZZY", "MATCH_CHOICES",
    "run_extract_news",
    "run_extract_news_genshin",
    "run_extract_news_genshin_en",
    "run_extract_news_zzz",
    "run_extract_news_starrail",
    "run_extract_tutorial",
    "run_extract_images",
    "run_extract_time",
    "run_extract_weibo",
    "run_export_excel",
    "export_to_excel",
    "run_filter",
]
