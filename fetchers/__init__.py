"""
抓取器模块
包含各种网站的数据抓取功能
"""

# 新闻抓取模块（无浏览器依赖的纯逻辑部分）
from .news import (
    GameNewsBaseScraper,
    GenshinNewsScraper,
    GenshinENNewsScraper,
    ZZZNewsScraper,
    SRNewsScraper,
    run_news_genshin,
    run_news_genshin_en,
    run_news_zzz,
    run_news_starrail,
)

# 向后兼容：旧的 run_news 指向原神新闻
run_news = run_news_genshin
NewsScraper = GenshinNewsScraper

# 其他抓取器（依赖 Playwright，延迟导入以支持无浏览器环境的测试）
_user_loaded = False
_baike_loaded = False
_tutorial_loaded = False
_custom_loaded = False
_weibo_loaded = False


def _lazy_load_user():
    global UserScraper, run_user, _user_loaded
    if not _user_loaded:
        from .user import UserScraper, run as run_user
        _user_loaded = True
    return UserScraper, run_user


def _lazy_load_baike():
    global BaikeScraper, run_baike, _baike_loaded
    if not _baike_loaded:
        from .baike import BaikeScraper, run as run_baike
        _baike_loaded = True
    return BaikeScraper, run_baike


def _lazy_load_tutorial():
    global TutorialScraper, run_tutorial, _tutorial_loaded
    if not _tutorial_loaded:
        from .tutorial import TutorialScraper, run as run_tutorial
        _tutorial_loaded = True
    return TutorialScraper, run_tutorial


def _lazy_load_custom():
    global CustomScraper, run_custom, _custom_loaded
    if not _custom_loaded:
        from .custom import CustomScraper, run as run_custom
        _custom_loaded = True
    return CustomScraper, run_custom


def _lazy_load_weibo():
    global WeiboScraper, run_weibo, _weibo_loaded
    if not _weibo_loaded:
        from .weibo import WeiboScraper, run as run_weibo
        _weibo_loaded = True
    return WeiboScraper, run_weibo


# 提供属性访问的惰性加载
def __getattr__(name):
    if name == "UserScraper":
        return _lazy_load_user()[0]
    if name == "run_user":
        return _lazy_load_user()[1]
    if name == "BaikeScraper":
        return _lazy_load_baike()[0]
    if name == "run_baike":
        return _lazy_load_baike()[1]
    if name == "TutorialScraper":
        return _lazy_load_tutorial()[0]
    if name == "run_tutorial":
        return _lazy_load_tutorial()[1]
    if name == "CustomScraper":
        return _lazy_load_custom()[0]
    if name == "run_custom":
        return _lazy_load_custom()[1]
    if name == "WeiboScraper":
        return _lazy_load_weibo()[0]
    if name == "run_weibo":
        return _lazy_load_weibo()[1]
    raise AttributeError(f"module 'fetchers' has no attribute '{name}'")


__all__ = [
    "UserScraper",
    "BaikeScraper",
    "NewsScraper",
    "TutorialScraper",
    "CustomScraper",
    "WeiboScraper",
    "GameNewsBaseScraper",
    "GenshinNewsScraper",
    "GenshinENNewsScraper",
    "ZZZNewsScraper",
    "SRNewsScraper",
    "run_user",
    "run_baike",
    "run_news",
    "run_news_genshin",
    "run_news_genshin_en",
    "run_news_zzz",
    "run_news_starrail",
    "run_tutorial",
    "run_custom",
    "run_weibo",
]
