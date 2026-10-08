"""配置管理（pydantic-settings + TOML）。

从 ``config.toml`` 加载强类型配置，支持环境变量覆盖（前缀 ``MIHOYO_``，
嵌套分隔符 ``__``）。

示例::

    MIHOYO_FETCH__HEADLESS=false
    MIHOYO_RETRY__MAX_ATTEMPTS=5

顶层需与 :class:`ToolkitSettings` 字段名对应。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from .paths import get_path_manager


class AppSettings(BaseModel):
    """应用级设置。"""

    mode: Literal["cli", "gui"] = "cli"
    version: str = "2.1.3"


class FetchSettings(BaseModel):
    """浏览器抓取行为设置。"""

    headless: bool = True
    wait_seconds: float = 3.0
    timeout: int = 120_000
    max_scroll_attempts: int = 500
    scroll_delay: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    browser_args: list[str] = Field(
        default_factory=lambda: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
    )


class RetrySettings(BaseModel):
    """重试策略（供 tenacity 使用）。"""

    max_attempts: int = Field(default=3, ge=1)
    delay: float = Field(default=2.0, ge=0)


class IncrementalSettings(BaseModel):
    """增量抓取 / 提取策略。"""

    enabled: bool = True
    stop_on_existing: bool = True
    merge_data: bool = True


class BackupSettings(BaseModel):
    """自动备份策略。"""

    enabled: bool = True
    max_backups: int = Field(default=10, ge=1)


class CookieSettings(BaseModel):
    """Cookie 免登录设置。"""

    use_firefox: bool = True


class UserSource(BaseModel):
    """米游社用户来源。"""

    url: str


class BaikeSource(BaseModel):
    """角色图鉴来源。"""

    url: str


class WeiboSource(BaseModel):
    """微博来源。"""

    url: str


class NewsSiteSource(BaseModel):
    """单个新闻站点（content_v2_user API）配置。"""

    url: str
    label: str
    scraper: str
    api_base_url: str
    api_chan_id: str
    api_page_param: str = "iPage"
    api_page_size_param: str = "iPageSize"
    api_page_size: int = 5
    api_lang_param: str = "sLangKey"
    api_lang_value: str = "zh-cn"
    api_app_id: str | None = None
    detail_url_pattern: str
    poster_ext_key: str | None = None
    lang_subdir: str | None = None
    expected_total: int | None = None

    def detail_url(self, info_id: int | str) -> str:
        """根据 iInfoId 拼接详情页链接。"""
        return self.detail_url_pattern.format(iInfoId=info_id)


class NewsSources(BaseModel):
    """四站点新闻来源集合，键为 game key。"""

    genshin: NewsSiteSource
    genshin_en: NewsSiteSource
    zzz: NewsSiteSource
    starrail: NewsSiteSource

    def keys(self) -> list[str]:
        """返回所有 game key（保持声明顺序）。"""
        return list(self.model_dump().keys())

    def get_site(self, game: str) -> NewsSiteSource:
        """按 game key 获取站点配置，非法 key 抛 KeyError。"""
        site = getattr(self, game, None)
        if site is None:
            raise KeyError(f"未知新闻站点: {game}")
        return site


class SourcesSettings(BaseModel):
    """所有数据来源配置。"""

    user: UserSource
    baike: BaikeSource
    weibo: WeiboSource
    news: NewsSources


class ToolkitSettings(BaseSettings):
    """工具箱根配置。"""

    model_config = SettingsConfigDict(
        env_prefix="MIHOYO_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    app: AppSettings = Field(default_factory=AppSettings)
    fetch: FetchSettings = Field(default_factory=FetchSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    incremental: IncrementalSettings = Field(default_factory=IncrementalSettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    cookies: CookieSettings = Field(default_factory=CookieSettings)
    sources: SourcesSettings

    @field_validator("sources")
    @classmethod
    def _require_sources(cls, value: SourcesSettings) -> SourcesSettings:
        if not value.news.keys():
            raise ValueError("至少需要配置一个新闻站点")
        return value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """优先级：init 参数 > 环境变量 > config.toml 文件。

        TOML 已由 pydantic-settings 原生支持；文件不存在时返回空源。
        """
        config_path = get_path_manager().config_file
        toml_source = TomlConfigSettingsSource(settings_cls, toml_file=config_path)
        return (init_settings, env_settings, toml_source, file_secret_settings)


@lru_cache(maxsize=1)
def get_settings() -> ToolkitSettings:
    """获取全局配置单例（进程内缓存）。

    ``sources`` 等字段由 TOML / 环境变量源在运行时注入，故此处忽略 mypy 的必填参数提示。
    """
    return ToolkitSettings()  # type: ignore[call-arg]


def reload_settings() -> ToolkitSettings:
    """清除缓存并重新加载配置。"""
    get_settings.cache_clear()
    return get_settings()


def load_settings(config_file: Path | None = None) -> ToolkitSettings:
    """从指定 TOML 文件加载配置（用于测试或自定义路径）。"""
    if config_file is None:
        return get_settings()
    data = TomlConfigSettingsSource(ToolkitSettings, toml_file=config_file)()
    return ToolkitSettings(**data)


__all__ = [
    "AppSettings",
    "BackupSettings",
    "BaikeSource",
    "CookieSettings",
    "FetchSettings",
    "IncrementalSettings",
    "NewsSiteSource",
    "NewsSources",
    "RetrySettings",
    "SourcesSettings",
    "ToolkitSettings",
    "UserSource",
    "WeiboSource",
    "get_settings",
    "load_settings",
    "reload_settings",
]
