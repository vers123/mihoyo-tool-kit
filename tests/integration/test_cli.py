"""根级入口 ``run.py`` 的参数解析冒烟测试（subprocess）。

覆盖非交互参数 ``--help`` / ``--version`` / ``--fetch`` / ``--export-excel`` /
``--count`` / ``--clean``：只验证 argparse 行为与约束，不联网、不实际抓取。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

#: 仓库根目录（本文件位于 tests/integration/ 下，故上溯三级）
REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRY = REPO_ROOT / "run.py"


def _run(*args: str, home: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if home is not None:
        env["MIHOYO_HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env=env,
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


def test_version_has_no_side_effects() -> None:
    """--version 是纯查询：不创建 data / logs / har 等运行时目录。"""
    with tempfile.TemporaryDirectory(prefix="mihoyo_cli_") as raw:
        home = Path(raw)
        result = _run("--version", home=home)
        assert result.returncode == 0, result.stderr
        assert "v" in result.stdout
        assert sorted(p.name for p in home.iterdir()) == []


def test_help_has_no_side_effects() -> None:
    """--help 同样不产生任何目录或日志文件。"""
    with tempfile.TemporaryDirectory(prefix="mihoyo_cli_") as raw:
        home = Path(raw)
        result = _run("--help", home=home)
        assert result.returncode == 0
        assert sorted(p.name for p in home.iterdir()) == []


def test_clean_yes_runs_without_prompt() -> None:
    """--clean --yes 非交互执行，且不因缺少输入而阻塞。"""
    with tempfile.TemporaryDirectory(prefix="mihoyo_cli_") as raw:
        home = Path(raw)
        (home / "config.toml").write_text(
            (REPO_ROOT / "config.toml").read_text(encoding="utf-8"), encoding="utf-8"
        )
        (home / "logs").mkdir()
        (home / "logs" / "app.log").write_text("x", encoding="utf-8")

        result = _run("--clean", "--yes", home=home)

        assert result.returncode == 0, result.stderr
        assert "完成" in result.stdout
        assert not (home / "logs" / "app.log").exists()
