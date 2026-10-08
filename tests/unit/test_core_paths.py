"""core.paths 单元测试。"""

from __future__ import annotations

from pathlib import Path

from mihoyo_toolkit.core.paths import PathManager, get_path_manager


def test_path_manager_default_layout(tmp_path: Path) -> None:
    pm = PathManager(root=tmp_path)
    assert pm.data == tmp_path / "data"
    assert pm.html == tmp_path / "data" / "html"
    assert pm.results == tmp_path / "data" / "results"
    assert pm.images == tmp_path / "data" / "images"
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
        pm.images,
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
