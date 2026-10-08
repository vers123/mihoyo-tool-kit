"""星穹铁道新闻提取。"""

from __future__ import annotations

from .base import GameNewsBaseExtractor


class SRNewsExtractor(GameNewsBaseExtractor):
    """星穹铁道新闻（sr.mihoyo.com/news，iChanId=255）。"""

    game = "starrail"


__all__ = ["SRNewsExtractor"]
