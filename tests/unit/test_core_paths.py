"""core.paths 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mihoyo_toolkit.core.exceptions import ConfigError
from mihoyo_toolkit.core.paths import (
    PathManager,
    app_data_root,
    get_path_manager,
    is_frozen,
    resolve_root,
)


def test_path_manager_default_layout(tmp_path: Path) -> None:
    pm = PathManager(root=tmp_path)
    assert pm.data == tmp_path / "data"
    assert pm.html == tmp_path / "data" / "html"
    assert pm.results == tmp_path / "data" / "results"
    assert pm.models == tmp_path / "data" / "models"
    assert pm.db == tmp_path / "data" / "toolkit.db"
    assert pm.backups == tmp_path / "data" / "backups"
    assert pm.logs == tmp_path / "logs"
    assert pm.har == tmp_path / "har"
    assert pm.output == tmp_path / "output"
    assert pm.resources == tmp_path / "resources"
    assert pm.fonts == tmp_path / "resources" / "font"
    assert pm.icons == tmp_path / "resources" / "icon"
    assert pm.config_file == tmp_path / "config.toml"
    assert pm.docs == tmp_path / "docs"


def test_path_manager_data_override(tmp_path: Path) -> None:
    custom = tmp_path / "custom-data"
    pm = PathManager(root=tmp_path, _data=custom)
    assert pm.data == custom
    assert pm.db == custom / "toolkit.db"


def test_har_dir(tmp_path: Path) -> None:
    pm = PathManager(root=tmp_path)
    assert pm.har_dir("news_genshin") == tmp_path / "har" / "news_genshin"


def test_ensure_dirs_creates_layout(tmp_path: Path) -> None:
    pm = PathManager(root=tmp_path)
    pm.ensure_dirs()
    for path in (
        pm.data,
        pm.html,
        pm.results,
        pm.models,
        pm.backups,
        pm.logs,
        pm.har,
        pm.output,
    ):
        assert path.is_dir()


def test_relative_inside_and_outside_root(tmp_path: Path) -> None:
    pm = PathManager(root=tmp_path)
    inside = tmp_path / "data" / "results" / "a.txt"
    inside.parent.mkdir(parents=True, exist_ok=True)
    inside.write_text("x", encoding="utf-8")
    assert pm.relative(inside) == str(Path("data") / "results" / "a.txt")

    outside = tmp_path.parent / "outside.txt"
    assert pm.relative(outside) == str(outside.resolve())


def test_get_path_manager_uses_env_home(tmp_home: Path) -> None:
    pm = get_path_manager()
    assert pm.root == tmp_home.resolve()


def test_get_path_manager_is_cached(tmp_home: Path) -> None:
    get_path_manager.cache_clear()
    assert get_path_manager() is get_path_manager()


def test_get_path_manager_data_dir_env(tmp_home: Path, monkeypatch) -> None:
    custom = tmp_home / "customdata"
    custom.mkdir()
    monkeypatch.setenv("MIHOYO_DATA_DIR", str(custom))
    get_path_manager.cache_clear()
    assert get_path_manager().data == custom.resolve()


def test_is_frozen_reflects_sys_attribute() -> None:
    """冻结环境由 ``sys.frozen`` 判定。"""
    original = getattr(sys, "frozen", None)
    try:
        sys.frozen = True  # type: ignore[attr-defined]
        assert is_frozen() is True
        del sys.frozen  # type: ignore[attr-defined]
        assert is_frozen() is False
    finally:
        if original is not None:  # pragma: no cover - 常规运行不会冻结
            sys.frozen = original  # type: ignore[attr-defined]


def test_resolve_root_prefers_env_home(tmp_path: Path, monkeypatch) -> None:
    """MIHOYO_HOME 优先且可写时直接采用。"""
    monkeypatch.setenv("MIHOYO_HOME", str(tmp_path))
    root, warning = resolve_root()
    assert root == tmp_path.resolve()
    assert warning is None


def test_resolve_root_rejects_unwritable_env_home(tmp_path: Path, monkeypatch) -> None:
    """显式设置的 MIHOYO_HOME 不可写时报错，不静默搬家。"""
    monkeypatch.setenv("MIHOYO_HOME", str(tmp_path))
    monkeypatch.setattr("mihoyo_toolkit.core.paths._is_writable", lambda _path: False)
    with pytest.raises(ConfigError):
        resolve_root()


def test_resolve_root_degrades_when_detected_root_unwritable(tmp_path: Path, monkeypatch) -> None:
    """自动探测的根不可写时降级到用户数据目录并给出告警。"""
    monkeypatch.delenv("MIHOYO_HOME", raising=False)
    monkeypatch.setattr("mihoyo_toolkit.core.paths._detect_project_root", lambda: tmp_path)
    monkeypatch.setattr("mihoyo_toolkit.core.paths._is_writable", lambda _path: False)
    app_dir = tmp_path / "appdata"
    monkeypatch.setattr("mihoyo_toolkit.core.paths.app_data_root", lambda: app_dir)

    root, warning = resolve_root()

    assert root == app_dir
    assert root.is_dir()
    assert warning and "降级" in warning


def test_frozen_root_uses_executable_dir(tmp_path: Path, monkeypatch) -> None:
    """冻结运行时根目录取可执行文件所在目录。"""
    exe = tmp_path / "app.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.delenv("MIHOYO_HOME", raising=False)
    monkeypatch.setattr("mihoyo_toolkit.core.paths.is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr("mihoyo_toolkit.core.paths._is_writable", lambda _path: True)

    root, warning = resolve_root()

    assert root == tmp_path.resolve()
    assert warning is None


def test_app_data_root_has_app_dir_name(monkeypatch, tmp_path: Path) -> None:
    """用户数据目录以应用名结尾。"""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert app_data_root() == (tmp_path / "mihoyo-toolkit").resolve()


def test_path_manager_carries_warning(tmp_path: Path) -> None:
    """PathManager 可携带降级告警，便于上层展示。"""
    pm = PathManager(root=tmp_path, warning="降级")
    assert pm.warning == "降级"
