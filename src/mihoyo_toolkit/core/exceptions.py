"""米游社工具箱 —— 异常类层级。

所有对外抛出的异常均继承自 :class:`MihoyoError`，便于统一捕获与分类处理。

层级::

    MihoyoError
    ├── ConfigError         配置缺失 / 非法
    ├── NetworkError        HTTP / 浏览器网络层失败
    │   ├── RetryExhausted  重试耗尽
    │   └── AuthError       登录态 / Cookie 失效
    ├── ParseError          页面 / API 响应解析失败
    ├── StorageError        SQLite / 文件读写失败
    └── ScraperError        抓取器通用错误
"""

from __future__ import annotations


class MihoyoError(Exception):
    """项目所有异常的基类。"""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        #: 附加上下文（响应片段、URL 等），用于日志排查
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - 简单拼接
        if self.detail:
            return f"{self.message} | {self.detail}"
        return self.message


class ConfigError(MihoyoError):
    """配置文件缺失、字段非法或路径不可用。"""


class NetworkError(MihoyoError):
    """HTTP 请求或浏览器网络层失败。"""


class RetryExhausted(NetworkError):
    """重试次数耗尽后仍失败。"""


class AuthError(NetworkError):
    """登录态失效（Cookie / Token 无效或需要重新登录）。"""


class ParseError(MihoyoError):
    """HTML / JSON 响应解析失败。"""


class StorageError(MihoyoError):
    """SQLite 或本地文件读写失败。"""


class ScraperError(MihoyoError):
    """抓取器运行期间的一般错误。"""


__all__ = [
    "AuthError",
    "ConfigError",
    "MihoyoError",
    "NetworkError",
    "ParseError",
    "RetryExhausted",
    "ScraperError",
    "StorageError",
]
