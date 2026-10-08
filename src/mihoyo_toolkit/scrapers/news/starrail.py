"""星穹铁道新闻抓取器。"""

from __future__ import annotations

from .base import GameNewsScraper, register_news


@register_news("starrail")
class SRNewsScraper(GameNewsScraper):
    """星穹铁道官网新闻（sr.mihoyo.com，iChanId=255）。"""

    game = "starrail"


def run_news_starrail(*, incremental: bool | None = None) -> int:
    """抓取星穹铁道新闻并落库。"""
    return SRNewsScraper("starrail", incremental=incremental).fetch_and_store()


__all__ = ["SRNewsScraper", "run_news_starrail"]
