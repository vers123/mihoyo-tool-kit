"""根级入口 ``run.py`` 的参数解析冒烟测试（subprocess）。

覆盖非交互参数 ``--help`` / ``--fetch`` / ``--export-excel`` / ``--count``：
只验证 argparse 行为与约束，不联网、不实际抓取。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

#: 仓库根目录（本文件位于 tests/integration/ 下，故上溯三级）
REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRY = REPO_ROOT / "run.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )


def test_help_lists_cli_args() -> None:
    """--help 应列出 --fetch / --export-excel / --count"""
    result = _run("--help")
    assert result.returncode == 0, result.stderr
    assert "--fetch" in result.stdout
    assert "--export-excel" in result.stdout
    assert "--count" in result.stdout


def test_invalid_fetch_choice_errors() -> None:
    """--fetch 非法值应被 argparse choices 拒绝"""
    result = _run("--fetch", "invalid")
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    assert "invalid" in combined or "choices" in combined


def test_count_runs_without_data() -> None:
    """--count 只读 SQLite，无数据时也应正常退出"""
    result = _run("--count")
    assert result.returncode == 0, result.stderr + result.stdout
