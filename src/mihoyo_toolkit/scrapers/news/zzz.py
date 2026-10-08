"""绝区零新闻抓取器。"""

from __future__ import annotations

from .base import GameNewsScraper, register_news


@register_news("zzz")
class ZZZNewsScraper(GameNewsScraper):
    """绝区零官网新闻（zzz.mihoyo.com，iChanId=273）。"""

    game = "zzz"


def run_news_zzz(*, incremental: bool | None = None) -> int:
    """抓取绝区零新闻并落库。"""
    return ZZZNewsScraper("zzz", incremental=incremental).fetch_and_store()


__all__ = ["ZZZNewsScraper", "run_news_zzz"]
