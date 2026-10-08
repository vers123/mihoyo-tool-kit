"""数据模型（pydantic v2）。

统一各来源的实体结构，供抓取、提取、存储、导出共享。

命名约定：字段沿用米哈游 API 原始名（``iInfoId`` / ``sTitle`` / ``dtStartTime``）
以降低映射成本，另提供 snake_case 别名属性。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

GameKey = Literal["genshin", "genshin_en", "zzz", "starrail"]


class NewsItem(BaseModel):
    """米哈游新闻条目（四站点统一）。"""

    model_config = ConfigDict(populate_by_name=True)

    #: 所属游戏 key（genshin / genshin_en / zzz / starrail）
    game: str
    iInfoId: int
    sTitle: str
    dtStartTime: str = ""
    sCategoryName: str = ""
    sIntro: str = ""
    poster_url: str = ""
    url: str

    #: 原始 API 条目（保留未映射字段，便于排查与扩展）
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @field_validator("dtStartTime", mode="before")
    @classmethod
    def _coerce_time(cls, value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value) if value is not None else ""

    @property
    def info_id(self) -> int:
        """iInfoId 的 snake_case 别名。"""
        return self.iInfoId

    @property
    def title(self) -> str:
        """sTitle 的 snake_case 别名。"""
        return self.sTitle

    @property
    def start_time(self) -> str:
        """dtStartTime 的 snake_case 别名。"""
        return self.dtStartTime

    @property
    def category(self) -> str:
        """sCategoryName 的 snake_case 别名。"""
        return self.sCategoryName

    @property
    def intro(self) -> str:
        """sIntro 的 snake_case 别名。"""
        return self.sIntro

    def sort_key(self) -> tuple[str, int]:
        """按 (时间, id) 排序的键，时间倒序用 reverse。"""
        return (self.dtStartTime, self.iInfoId)


class PostItem(BaseModel):
    """米游社用户发帖。"""

    model_config = ConfigDict(populate_by_name=True)

    post_id: str
    title: str = ""
    created_at: str = ""
    url: str = ""
    content: str = ""

    @property
    def sort_key(self) -> str:
        return self.created_at


class WeiboItem(BaseModel):
    """微博帖子。"""

    model_config = ConfigDict(populate_by_name=True)

    #: mblogid（兼容 bid / mid / idstr 回退）
    post_id: str
    text: str = ""
    created_at: str = ""
    url: str = ""
    reposts: int = 0
    comments: int = 0
    attitudes: int = 0

    @property
    def sort_key(self) -> str:
        return self.created_at


class TutorialItem(BaseModel):
    """教程角色数据项。"""

    model_config = ConfigDict(populate_by_name=True)

    character_id: str
    name: str = ""
    #: 页面语言（zh-cn / en-us / default）
    lang: str = ""

    @property
    def sort_key(self) -> str:
        return self.character_id


class ImageItem(BaseModel):
    """图鉴图片链接。"""

    model_config = ConfigDict(populate_by_name=True)

    character_id: str = ""
    name: str = ""
    image_url: str

    @property
    def sort_key(self) -> str:
        return self.image_url


class ChangelogEntry(BaseModel):
    """教程更新日志条目。"""

    model_config = ConfigDict(populate_by_name=True)

    version: str = ""
    date: str = ""
    content: str = ""

    @property
    def sort_key(self) -> str:
        return self.date


#: 各实体在 SQLite 中的表名映射
ENTITY_TABLES: dict[str, str] = {
    "news": "news",
    "post": "posts",
    "weibo": "weibo",
    "tutorial": "tutorial",
    "image": "images",
}


__all__ = [
    "ENTITY_TABLES",
    "ChangelogEntry",
    "GameKey",
    "ImageItem",
    "NewsItem",
    "PostItem",
    "TutorialItem",
    "WeiboItem",
]
