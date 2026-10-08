"""utils.backup_manager 单元测试。"""

from __future__ import annotations

import os
from pathlib import Path

from mihoyo_toolkit.core.storage import Storage
from mihoyo_toolkit.utils.backup_manager import BackupInfo, BackupManager, backup_manager


def test_backup_dir_defaults_to_path_manager(tmp_home: Path) -> None:
    manager = BackupManager()
    assert manager.backup_dir == tmp_home / "data" / "backups"
    assert manager.backup_dir.is_dir()


def test_backup_dir_custom(tmp_path: Path) -> None:
    custom = tmp_path / "my-backups"
    manager = BackupManager(custom)
    assert manager.backup_dir == custom
    assert custom.is_dir()


def test_max_backups_from_settings() -> None:
    assert BackupManager().max_backups == 3


def test_subdir_name() -> None:
    assert BackupManager._subdir_name("toolkit.db") == "toolkit"
    assert BackupManager._subdir_name("noext") == "noext"


def test_backup_file_and_list(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    source = tmp_path / "posts.txt"
    source.write_text("hello", encoding="utf-8")

    info = manager.backup_file(source, reason="unit")
    assert isinstance(info, BackupInfo)
    assert info.size > 0
    assert "unit" in info.filename
    assert info.filename.startswith("posts_")
    assert info.filepath.is_file()

    backups = manager.list_backups("posts.txt")
    assert len(backups) == 1
    assert backups[0].filename == info.filename


def test_backup_file_missing_source(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    assert manager.backup_file(tmp_path / "nope.txt") is None


def test_list_backups_unknown_file(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    assert manager.list_backups("unknown.txt") == []


def test_backup_database_missing(tmp_home: Path) -> None:
    manager = BackupManager()
    assert manager.backup_database() is None


def test_backup_database_success(tmp_home: Path) -> None:
    with Storage() as store:
        store.count_news()  # 触发建库

    manager = BackupManager()
    info = manager.backup_database()
    assert info is not None
    assert info.filepath.is_file()
    assert info.filename.startswith("toolkit_")


def test_list_backups_sorted_desc(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    source = tmp_path / "data.txt"
    source.write_text("x", encoding="utf-8")

    subdir = manager.backup_dir / "data"
    subdir.mkdir(parents=True, exist_ok=True)
    base = 1_600_000_000
    names = [
        "data_20240101_000000.txt",
        "data_20240102_000000.txt",
        "data_20240103_000000.txt",
    ]
    for index, name in enumerate(names):
        path = subdir / name
        path.write_text("x", encoding="utf-8")
        os.utime(path, (base + index, base + index))

    backups = manager.list_backups("data.txt")
    assert [b.filename for b in backups] == list(reversed(names))


def test_restore_backup(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    backup = tmp_path / "backup.txt"
    backup.write_text("backup-data", encoding="utf-8")
    target = tmp_path / "out" / "target.txt"

    assert manager.restore_backup(backup, target) is True
    assert target.read_text(encoding="utf-8") == "backup-data"


def test_restore_backup_overwrites_and_safety_copies(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    backup = tmp_path / "backup.txt"
    backup.write_text("new", encoding="utf-8")
    target = tmp_path / "target.txt"
    target.write_text("old", encoding="utf-8")

    assert manager.restore_backup(backup, target) is True
    assert target.read_text(encoding="utf-8") == "new"
    safety = list(tmp_path.glob("target.txt.before_restore_*"))
    assert len(safety) == 1


def test_restore_backup_missing(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    assert manager.restore_backup(tmp_path / "nope.txt", tmp_path / "t.txt") is False


def test_prune_keeps_newest(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    subdir = manager.backup_dir / "data"
    subdir.mkdir(parents=True, exist_ok=True)
    for i in range(4):
        (subdir / f"data_{i}.txt").write_text("x", encoding="utf-8")

    removed = manager.prune(2)
    assert removed == 2
    assert len(list(subdir.iterdir())) == 2


def test_backup_file_auto_prune(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path / "bk")
    source = tmp_path / "auto.txt"
    source.write_text("data", encoding="utf-8")

    # 预置 4 份旧备份，再过备份一次应触发自动清理（保留 max_backups=3）
    subdir = manager.backup_dir / "auto"
    subdir.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        (subdir / f"auto_old{index}.txt").write_text("x", encoding="utf-8")

    assert manager.backup_file(source) is not None
    assert len(list(subdir.iterdir())) == 3


def test_backup_file_same_second_creates_distinct_backups(tmp_path: Path) -> None:
    """回归：同一秒内的多次备份不应互相覆盖（时间戳含微秒）。"""
    manager = BackupManager(tmp_path / "bk")
    source = tmp_path / "rapid.txt"
    source.write_text("data", encoding="utf-8")

    first = manager.backup_file(source)
    second = manager.backup_file(source)

    assert first is not None and second is not None
    assert first.filepath != second.filepath
    assert len(manager.list_backups("rapid.txt")) == 2


def test_singleton_exists() -> None:
    assert isinstance(backup_manager, BackupManager)
