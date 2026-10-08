"""GUI 页面集合。"""

from __future__ import annotations

from .base import BasePage
from .filter import FilterPage
from .news import NewsPage
from .other import OtherPage
from .preview_dialog import PreviewDialog
from .system import ExportPage, SystemPage
from .user_posts import UserPostsPage
from .weibo import WeiboPage

__all__ = [
    "BasePage",
    "ExportPage",
    "FilterPage",
    "NewsPage",
    "OtherPage",
    "PreviewDialog",
    "SystemPage",
    "UserPostsPage",
    "WeiboPage",
]
