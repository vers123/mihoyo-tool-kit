"""原神英文版新闻提取。"""

from __future__ import annotations

from .base import GameNewsBaseExtractor


class GenshinENNewsExtractor(GameNewsBaseExtractor):
    """原神英文版新闻（genshin.hoyoverse.com/en/news）。"""

    game = "genshin_en"


__all__ = ["GenshinENNewsExtractor"]
