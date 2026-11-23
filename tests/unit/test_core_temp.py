"""core.temp 单元测试（临时文件统一入口）。"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from mihoyo_toolkit.core.temp import (
    STALE_AGE_SECONDS,
    TEMP_PREFIX,
    TempError,
    sweep_stale_temp,
    temp_root,
    temp_workspace,
)


def test_temp_root_is_system_temp(monkeypatch) -> None:
    """默认临时根就是系统临时目录。"""
    monkeypatch.delenv("MIHOYO_TEMP_DIR", raising=False)
    import tempfile

    assert temp_root() == Path(tempfile.gettempdir()).resolve()


def test_temp_root_honours_env_override(monkeypatch, tmp_path: Path) -> None:
    """MIHOYO_TEMP_DIR 可覆盖临时根。"""
    custom = tmp_path / "mytemp"
    monkeypatch.setenv("MIHOYO_TEMP_DIR", str(custom))
    root = temp_root()
    assert root == custom.resolve()
    assert root.is_dir()


def test_temp_root_raises_when_unwritable(monkeypatch, tmp_path: Path) -> None:
    """显式指定的临时目录不可用时抛 TempError，而不是静默写进仓库。"""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)
    monkeypatch.setenv("MIHOYO_TEMP_DIR", str(blocked))
    monkeypatch.setattr("mihoyo_toolkit.core.temp.os.access", lambda *_args: False)
    try:
        with pytest.raises(TempError):
            temp_root()
    finally:
        blocked.chmod(0o700)


def test_temp_workspace_lives_under_temp_root_and_is_cleaned(monkeypatch, tmp_path: Path) -> None:
    """工作区位于临时根下，退出后递归删除。"""
    monkeypatch.setenv("MIHOYO_TEMP_DIR", str(tmp_path))
    with temp_workspace() as workdir:
        assert workdir.parent == tmp_path.resolve()
        assert workdir.name.startswith(TEMP_PREFIX)
        nested = workdir / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "f.txt").write_text("x", encoding="utf-8")
    assert not workdir.exists()


def test_temp_workspace_cleans_on_exception(monkeypatch, tmp_path: Path) -> None:
    """异常路径同样清理临时工作区。"""
    monkeypatch.setenv("MIHOYO_TEMP_DIR", str(tmp_path))
    with pytest.raises(RuntimeError), temp_workspace() as workdir:
        (workdir / "f.txt").write_text("x", encoding="utf-8")
        raise RuntimeError("boom")
    assert not workdir.exists()


def test_sweep_stale_temp_removes_only_old_prefixed_dirs(tmp_path: Path) -> None:
    """只清理本项目前缀且超龄的目录。"""
    old = tmp_path / f"{TEMP_PREFIX}old"
    fresh = tmp_path / f"{TEMP_PREFIX}fresh"
    foreign = tmp_path / "other-tool-old"
    for path in (old, fresh, foreign):
        path.mkdir()

    stale_time = time.time() - STALE_AGE_SECONDS - 60
    import os

    os.utime(old, (stale_time, stale_time))
    os.utime(foreign, (stale_time, stale_time))

    removed = sweep_stale_temp(base=tmp_path)

    assert removed == 1
    assert not old.exists()
    assert fresh.is_dir()
    assert foreign.is_dir()


def test_sweep_stale_temp_keeps_current_session(tmp_path: Path) -> None:
    """当前会话目录即使超龄也保留。"""
    current = tmp_path / f"{TEMP_PREFIX}current"
    current.mkdir()
    stale_time = time.time() - STALE_AGE_SECONDS - 60
    import os

    os.utime(current, (stale_time, stale_time))

    assert sweep_stale_temp(base=tmp_path, keep=current) == 0
    assert current.is_dir()


def test_sweep_stale_temp_handles_missing_base(tmp_path: Path) -> None:
    """基准目录不存在时返回 0，不抛异常。"""
    assert sweep_stale_temp(base=tmp_path / "missing") == 0
