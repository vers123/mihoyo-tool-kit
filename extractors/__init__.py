from .tutorial import TutorialExtractor, ChangelogExtractor, run as run_extract_tutorial
from .images import ImageExtractor, run as run_extract_images
from .time import PostExtractor, run as run_extract_time
from .weibo import WeiboExtractor, run as run_extract_weibo
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

# Excel 导出采用懒加载：仅在实际调用时才导入 openpyxl，
# 避免 extractors 包整体被强制依赖 openpyxl（提升 CLI/非 Excel 场景启动速度）。
def run_export_excel(*args, **kwargs):
    from .excel_writer import run as _run
    return _run(*args, **kwargs)

def export_to_excel(*args, **kwargs):
    from .excel_writer import export_to_excel as _export
    return _export(*args, **kwargs)

# 向后兼容：旧的 NewsExtractor / run_extract_news 指向原神新闻提取
NewsExtractor = GenshinNewsExtractor
run_extract_news = run_extract_news_genshin

__all__ = [
    "NewsExtractor",
    "TutorialExtractor",
    "ChangelogExtractor",
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
