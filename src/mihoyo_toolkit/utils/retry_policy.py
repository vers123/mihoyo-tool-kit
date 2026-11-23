"""重试策略构造（每次调用读取当前配置）。

多数抓取模块原先在 **import 时** 读取 ``get_settings()`` 并据此构造 ``@retry``，
导致 ``reload_settings()``（菜单改配置、GUI 保存配置）后重试次数与间隔不生效。

这里提供 :func:`with_retry`：装饰后的函数**每次调用**都按当前 ``[retry]`` 配置
重新构造 tenacity 策略，因此配置改动立即生效。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from ..core.config import get_settings

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """一次重试策略的快照（供测试与日志使用）。"""

    max_attempts: int
    delay: float


def current_policy() -> RetryPolicy:
    """读取当前配置中的重试策略。"""
    retry_settings = get_settings().retry
    return RetryPolicy(max_attempts=retry_settings.max_attempts, delay=retry_settings.delay)


def with_retry(
    exception_types: type[BaseException] | tuple[type[BaseException], ...] = Exception,
) -> Callable[[F], F]:
    """装饰器：按当前配置对函数重试（配置在每次调用时读取）。

    Args:
        exception_types: 触发重试的异常类型；默认 ``Exception``（与 tenacity 默认一致）。
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            policy = current_policy()
            decorated = retry(
                stop=stop_after_attempt(policy.max_attempts),
                wait=wait_fixed(policy.delay),
                retry=retry_if_exception_type(exception_types),
                reraise=True,
            )(func)
            return decorated(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def attempts() -> Iterable[int]:
    """返回 1..max_attempts 的迭代器（便于调用方做显式重试计数）。"""
    return range(1, current_policy().max_attempts + 1)


__all__ = ["RetryPolicy", "attempts", "current_policy", "with_retry"]
