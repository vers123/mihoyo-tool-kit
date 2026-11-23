"""utils.retry_policy 单元测试（配置改动即时生效）。"""

from __future__ import annotations

import pytest

from mihoyo_toolkit.core.config import get_settings, reload_settings
from mihoyo_toolkit.utils.retry_policy import current_policy, with_retry


def test_current_policy_reads_settings(tmp_home) -> None:
    """策略来自 [retry] 配置。"""
    policy = current_policy()
    assert policy.max_attempts == get_settings().retry.max_attempts
    assert policy.delay == get_settings().retry.delay


def test_with_retry_uses_latest_settings(monkeypatch) -> None:
    """重试次数在调用时读取，reload_settings 后立即生效。"""
    monkeypatch.setenv("MIHOYO_RETRY__MAX_ATTEMPTS", "3")
    monkeypatch.setenv("MIHOYO_RETRY__DELAY", "0")
    reload_settings()

    calls: list[int] = []

    @with_retry(ValueError)
    def boom() -> None:
        calls.append(1)
        raise ValueError("nope")

    with pytest.raises(ValueError):
        boom()
    assert len(calls) == 3

    monkeypatch.setenv("MIHOYO_RETRY__MAX_ATTEMPTS", "1")
    reload_settings()
    calls.clear()
    with pytest.raises(ValueError):
        boom()
    assert len(calls) == 1


def test_with_retry_returns_value(tmp_home) -> None:
    """成功调用直接返回结果，不额外重试。"""
    calls: list[int] = []

    @with_retry(ValueError)
    def ok() -> int:
        calls.append(1)
        return 7

    assert ok() == 7
    assert calls == [1]


def test_with_retry_does_not_catch_other_exceptions(tmp_home) -> None:
    """未声明的异常类型不重试。"""
    calls: list[int] = []

    @with_retry(ValueError)
    def boom() -> None:
        calls.append(1)
        raise TypeError("other")

    with pytest.raises(TypeError):
        boom()
    assert calls == [1]
