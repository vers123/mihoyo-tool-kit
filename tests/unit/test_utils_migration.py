"""utils.migration 单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from mihoyo_toolkit.core.exceptions import MihoyoError
from mihoyo_toolkit.utils import migration
from mihoyo_toolkit.utils.migration import DataMigrationManager, check_and_migrate


def test_no_legacy_dir(tmp_home: Path) -> None:
    manager = DataMigrationManager()
    assert manager.legacy_dir is None
    assert manager.needs_migration() is False
    result = manager.run_migration()
    assert result == {
        "success": True,
        "migrated_files": [],
        "skipped_files": [],
        "errors": [],
    }


def test_legacy_dir_from_env(tmp_path: Path, monkeypatch) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    monkeypatch.setenv("MIHOYO_LEGACY_DIR", str(legacy))
    manager = DataMigrationManager()
    assert manager.legacy_dir == legacy


def test_target_path_without_legacy_raises(tmp_home: Path) -> None:
    manager = DataMigrationManager()
    with pytest.raises(MihoyoError):
        manager._target_path(Path("x.html"))


def test_new_name_mapping() -> None:
    assert DataMigrationManager._new_name("news_page.html") == "genshin_news.html"
    assert DataMigrationManager._new_name("news.txt") == "genshin_news.txt"
    assert DataMigrationManager._new_name("hero_page.html") == "hero_news.html"
    assert DataMigrationManager._new_name("plain.txt") == "plain.txt"


def _make_legacy_data(tmp_path: Path) -> Path:
    legacy = tmp_path / "legacy" / "data"
    (legacy / "html").mkdir(parents=True)
    (legacy / "images").mkdir(parents=True)
    (legacy / "news_page.html").write_text("<html>news</html>", encoding="utf-8")
    (legacy / "html" / "hero_page.html").write_text("<html>hero</html>", encoding="utf-8")
    (legacy / "plain.txt").write_text("text", encoding="utf-8")
    (legacy / "images" / "pics.txt").write_text("pics", encoding="utf-8")
    return legacy


def test_migration_flow(tmp_path: Path, tmp_home: Path) -> None:
    legacy = _make_legacy_data(tmp_path)

    manager = DataMigrationManager(legacy)
    assert manager.needs_migration() is True

    result = manager.run_migration()
    assert result["success"] is True
    assert len(result["migrated_files"]) == 4
    assert result["errors"] == []

    assert (tmp_home / "data" / "html" / "genshin_news.html").is_file()
    assert (tmp_home / "data" / "html" / "hero_news.html").is_file()
    assert (tmp_home / "data" / "results" / "plain.txt").is_file()
    assert (tmp_home / "data" / "images" / "pics.txt").is_file()

    # 幂等：目标已存在则不再迁移
    assert manager.needs_migration() is False
    second = manager.run_migration()
    assert second["migrated_files"] == []


def test_warn_legacy_config(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    config = legacy / "config.json"
    config.write_text("{}", encoding="utf-8")

    manager = DataMigrationManager(legacy)
    assert manager.warn_legacy_config() == config
    result = manager.run_migration()
    assert result["success"] is True


def test_run_migration_records_errors(tmp_path: Path, monkeypatch) -> None:
    legacy = _make_legacy_data(tmp_path)
    manager = DataMigrationManager(legacy)

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(migration.shutil, "copy2", boom)
    result = manager.run_migration()

    assert result["success"] is False
    assert result["errors"]


def test_check_and_migrate_without_legacy() -> None:
    # 未配置旧目录：不应抛异常
    check_and_migrate()


def test_check_and_migrate_with_legacy(tmp_path: Path, tmp_home: Path, monkeypatch) -> None:
    legacy = _make_legacy_data(tmp_path)
    monkeypatch.setenv("MIHOYO_LEGACY_DIR", str(legacy.parent))

    check_and_migrate()

    assert (tmp_home / "data" / "html" / "genshin_news.html").is_file()
