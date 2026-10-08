"""原神新闻提取（中文）。"""

from __future__ import annotations

from .base import GameNewsBaseExtractor


class GenshinNewsExtractor(GameNewsBaseExtractor):
    """原神官网新闻（ys.mihoyo.com，iChanId=719）。"""

    game = "genshin"


__all__ = ["GenshinNewsExtractor"]
