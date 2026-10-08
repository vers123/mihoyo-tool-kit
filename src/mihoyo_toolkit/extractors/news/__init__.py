"""四站点新闻提取（SQLite → TXT）。

对外统一入口 :func:`run_extract_news`，按 ``game`` 分派到对应子类。
"""

from __future__ import annotations

from ...utils.logger import get_module_logger
from .base import GameNewsBaseExtractor
from .genshin import GenshinNewsExtractor
from .genshin_en import GenshinENNewsExtractor
from .starrail import SRNewsExtractor
from .zzz import ZZZNewsExtractor

logger = get_module_logger("extractors.news")

#: game key → 提取器类（子类仅声明 game，此处据其构建注册表）
NEWS_EXTRACTORS: dict[str, type[GameNewsBaseExtractor]] = {
    cls.game: cls
    for cls in (
        GenshinNewsExtractor,
        GenshinENNewsExtractor,
        ZZZNewsExtractor,
        SRNewsExtractor,
    )
}


def run_extract_news(game: str, incremental: bool = False) -> None:
    """导出指定游戏的新闻 TXT 到 ``data/results/{results_subdir}/{game}_news.txt``。"""
    extractor_cls = NEWS_EXTRACTORS.get(game)
    if extractor_cls is None:
        logger.error("未知新闻站点: %s（可用: %s）", game, sorted(NEWS_EXTRACTORS))
        return
    extractor_cls().export(incremental=incremental)


__all__ = [
    "NEWS_EXTRACTORS",
    "GameNewsBaseExtractor",
    "GenshinENNewsExtractor",
    "GenshinNewsExtractor",
    "SRNewsExtractor",
    "ZZZNewsExtractor",
    "run_extract_news",
]
