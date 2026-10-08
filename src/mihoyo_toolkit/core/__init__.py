"""核心模块：配置、路径、存储、模型、异常。"""

from __future__ import annotations

from .config import ToolkitSettings, get_settings, reload_settings
from .exceptions import (
    AuthError,
    ConfigError,
    GuiError,
    MihoyoError,
    NetworkError,
    ParseError,
    RetryExhausted,
    ScraperError,
    StorageError,
)
from .models import (
    ChangelogEntry,
    ImageItem,
    NewsItem,
    PostItem,
    TutorialItem,
    WeiboItem,
)
from .paths import PathManager, get_path_manager
from .storage import Storage

__all__ = [
    # 配置
    "ToolkitSettings",
    "get_settings",
    "reload_settings",
    # 路径
    "PathManager",
    "get_path_manager",
    # 存储
    "Storage",
    # 模型
    "NewsItem",
    "PostItem",
    "WeiboItem",
    "TutorialItem",
    "ImageItem",
    "ChangelogEntry",
    # 异常
    "MihoyoError",
    "ConfigError",
    "NetworkError",
    "RetryExhausted",
    "AuthError",
    "ParseError",
    "StorageError",
    "ScraperError",
    "GuiError",
]
