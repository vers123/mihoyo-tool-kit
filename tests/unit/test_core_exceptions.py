"""core.exceptions 单元测试。"""

from __future__ import annotations

import pytest

from mihoyo_toolkit.core.exceptions import (
    AuthError,
    ConfigError,
    MihoyoError,
    NetworkError,
    ParseError,
    RetryExhausted,
    ScraperError,
    StorageError,
)


def test_mihoyo_error_message_and_detail() -> None:
    err = MihoyoError("boom", detail="ctx")
    assert err.message == "boom"
    assert err.detail == "ctx"
    assert str(err) == "boom | ctx"


def test_mihoyo_error_without_detail() -> None:
    err = MihoyoError("boom")
    assert err.detail is None
    assert str(err) == "boom"


def test_error_hierarchy() -> None:
    assert issubclass(ConfigError, MihoyoError)
    assert issubclass(NetworkError, MihoyoError)
    assert issubclass(RetryExhausted, NetworkError)
    assert issubclass(AuthError, NetworkError)
    assert issubclass(ParseError, MihoyoError)
    assert issubclass(StorageError, MihoyoError)
    assert issubclass(ScraperError, MihoyoError)


def test_subclasses_are_catchable_as_base() -> None:
    with pytest.raises(MihoyoError):
        raise StorageError("db down")
    with pytest.raises(NetworkError):
        raise RetryExhausted("retries exhausted")
