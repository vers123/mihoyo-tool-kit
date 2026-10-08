"""
新闻提取模块
支持原神（中/英文）、绝区零、星穹铁道的新闻数据提取
基于 content_v2_user 统一 API 架构生成的 HTML
"""

from .base import GameNewsBaseExtractor, NewsItem
from .genshin import GenshinNewsExtractor, run as run_extract_news_genshin
from .genshin_en import GenshinENNewsExtractor, run as run_extract_news_genshin_en
from .zzz import ZZZNewsExtractor, run as run_extract_news_zzz
from .starrail import SRNewsExtractor, run as run_extract_news_starrail

__all__ = [
    "GameNewsBaseExtractor",
    "NewsItem",
    "GenshinNewsExtractor",
    "GenshinENNewsExtractor",
    "ZZZNewsExtractor",
    "SRNewsExtractor",
    "run_extract_news_genshin",
    "run_extract_news_genshin_en",
    "run_extract_news_zzz",
    "run_extract_news_starrail",
]
