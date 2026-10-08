"""utils.logger 单元测试。"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pytest

from mihoyo_toolkit.utils.logger import (
    append_gui_log,
    get_module_logger,
    log_function_call,
    setup_console_log,
    setup_logger,
)

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")


def test_setup_logger_writes_app_log(tmp_home: Path) -> None:
    logger = setup_logger("mihoyo_toolkit.testlogger", logging.DEBUG)
    logger.debug("hello-logger")
    for handler in logger.handlers:
        handler.flush()

    app_log = tmp_home / "logs" / "app.log"
    assert app_log.is_file()
    assert "hello-logger" in app_log.read_text(encoding="utf-8")


def test_get_module_logger_name() -> None:
    logger = get_module_logger("mymodule")
    assert logger.name == "mihoyo_toolkit.mymodule"


def test_append_gui_log_adds_timestamp(tmp_home: Path) -> None:
    append_gui_log("first message")
    content = (tmp_home / "logs" / "gui.log").read_text(encoding="utf-8")
    assert _TS_RE.match(content)
    assert content.strip().endswith("first message")


def test_append_gui_log_keeps_existing_timestamp(tmp_home: Path) -> None:
    append_gui_log("2024-01-01 00:00:00 already stamped")
    content = (tmp_home / "logs" / "gui.log").read_text(encoding="utf-8").strip()
    assert content == "2024-01-01 00:00:00 already stamped"


def test_log_function_call_success() -> None:
    @log_function_call
    def add(a: int, b: int) -> int:
        return a + b

    assert add(1, 2) == 3
    assert add.__name__ == "add"


def test_log_function_call_reraises() -> None:
    @log_function_call
    def boom() -> None:
        raise ValueError("nope")

    with pytest.raises(ValueError):
        boom()


def test_setup_console_log_idempotent(tmp_home: Path) -> None:
    original_stdout, original_stderr = sys.stdout, sys.stderr
    try:
        sys._mihoyo_console_configured = False
        setup_console_log()
        first_stdout = sys.stdout
        assert first_stdout is not original_stdout
        assert (tmp_home / "logs" / "console.log").is_file()

        setup_console_log()  # 幂等：不再替换
        assert sys.stdout is first_stdout
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        if hasattr(sys, "_mihoyo_console_configured"):
            del sys._mihoyo_console_configured
