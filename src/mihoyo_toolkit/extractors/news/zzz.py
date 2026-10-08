"""绝区零新闻提取。"""

from __future__ import annotations

from .base import GameNewsBaseExtractor


class ZZZNewsExtractor(GameNewsBaseExtractor):
    """绝区零新闻（zzz.mihoyo.com/news，iChanId=273）。"""

    game = "zzz"


__all__ = ["ZZZNewsExtractor"]
