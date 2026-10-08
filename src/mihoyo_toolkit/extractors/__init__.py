"""数据提取模块。

v2 架构下新闻 / 发帖 / 微博 / 图片均由抓取层直写 SQLite，提取层负责读库并
导出为 ``data/results`` 下的 TXT；教程仍保留 HTML 解析（同时落库 + 导出）。
"""

from __future__ import annotations

from .images import ImageExtractor, run_extract_images
from .news import (
    GameNewsBaseExtractor,
    GenshinENNewsExtractor,
    GenshinNewsExtractor,
    SRNewsExtractor,
    ZZZNewsExtractor,
    run_extract_news,
)
from .posts import PostExtractor, run_extract_posts
from .tutorial import ChangelogExtractor, TutorialExtractor, run_extract_tutorial
from .weibo import WeiboExtractor, run_extract_weibo

__all__ = [
    # 提取器类
    "ChangelogExtractor",
    "GameNewsBaseExtractor",
    "GenshinENNewsExtractor",
    "GenshinNewsExtractor",
    "ImageExtractor",
    "PostExtractor",
    "SRNewsExtractor",
    "TutorialExtractor",
    "WeiboExtractor",
    "ZZZNewsExtractor",
    # 运行入口
    "run_extract_images",
    "run_extract_news",
    "run_extract_posts",
    "run_extract_tutorial",
    "run_extract_weibo",
]
