"""工具模块：日志、HAR、Cookie、备份、迁移、TXT 过滤。"""

from __future__ import annotations

from .backup_manager import BackupInfo, BackupManager, backup_manager
from .cookie_loader import find_firefox_profile, load_firefox_cookies
from .har_loader import (
    find_har_file,
    get_har_dir,
    get_har_welcome_html,
    get_har_welcome_text,
    load_har_entries,
    parse_har_file,
    print_har_instructions,
)
from .logger import (
    append_gui_log,
    get_module_logger,
    log_function_call,
    setup_console_log,
    setup_logger,
)
from .migration import DataMigrationManager, check_and_migrate
from .txt_filter import MatchResult, TxtFilter, run_filter

__all__ = [
    # 日志
    "setup_console_log",
    "setup_logger",
    "get_module_logger",
    "append_gui_log",
    "log_function_call",
    # HAR
    "find_har_file",
    "get_har_dir",
    "get_har_welcome_html",
    "get_har_welcome_text",
    "load_har_entries",
    "parse_har_file",
    "print_har_instructions",
    # Cookie
    "find_firefox_profile",
    "load_firefox_cookies",
    # 备份
    "BackupInfo",
    "BackupManager",
    "backup_manager",
    # 迁移
    "DataMigrationManager",
    "check_and_migrate",
    # TXT 过滤
    "MatchResult",
    "TxtFilter",
    "run_filter",
]
