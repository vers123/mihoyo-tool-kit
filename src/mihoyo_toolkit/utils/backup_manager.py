"""备份管理器.

在数据更新 / 迁移前对关键文件 (含 SQLite 数据库) 创建带时间戳的备份,
并提供列举, 恢复与按份数清理能力.

备份目录统一来自 :func:`get_path_manager` 的 ``backups``, 每个源文件
对应一个以其文件名为名的子目录, 避免不同文件的备份相互混淆.
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from ..core.config import get_settings
from ..core.exceptions import StorageError
from ..core.paths import get_path_manager
from .logger import get_module_logger

logger = get_module_logger("backup_manager")

#: 备份文件名时间戳（含微秒，避免同一秒内多次备份相互覆盖）
_TS_FORMAT = "%Y%m%d_%H%M%S_%f"


class BackupInfo(BaseModel):
    """单个备份文件的元信息."""

    filename: str
    filepath: Path
    size: int
    created_at: datetime


class BackupManager:
    """文件 / 数据库备份管理器."""

    def __init__(self, backup_dir: Path | None = None) -> None:
        #: 自定义备份根目录; 为 None 时使用 PathManager 的 backups 目录
        self._backup_dir = backup_dir

    # ------------------------------------------------------------------ #
    #  目录与配置
    # ------------------------------------------------------------------ #
    @property
    def backup_dir(self) -> Path:
        """备份根目录 (不存在时自动创建)."""
        base = self._backup_dir or get_path_manager().backups
        base.mkdir(parents=True, exist_ok=True)
        return base

    @property
    def max_backups(self) -> int:
        """每个源文件保留的最大备份份数 (来自配置)."""
        return get_settings().backup.max_backups

    @staticmethod
    def _subdir_name(filename: str) -> str:
        """由源文件名推导备份子目录名."""
        path = Path(filename)
        return path.stem or path.name

    def _subdir(self, filename: str) -> Path:
        """确保并返回指定文件的备份子目录."""
        sub = self.backup_dir / self._subdir_name(filename)
        sub.mkdir(parents=True, exist_ok=True)
        return sub

    @staticmethod
    def _info_from_path(path: Path) -> BackupInfo:
        stat = path.stat()
        return BackupInfo(
            filename=path.name,
            filepath=path,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime),
        )

    # ------------------------------------------------------------------ #
    #  备份
    # ------------------------------------------------------------------ #
    def backup_file(self, source: Path, *, reason: str = "") -> BackupInfo | None:
        """备份单个文件.

        Args:
            source: 源文件路径.
            reason: 备份原因 (可选), 会写入备份文件名便于识别.

        Returns:
            备份信息; 源文件不存在时返回 None, 写入失败时抛 :class:`StorageError`.
        """
        source = Path(source)
        if not source.is_file():
            logger.warning("源文件不存在, 无需备份: %s", source)
            return None

        timestamp = datetime.now().strftime(_TS_FORMAT)
        if reason:
            name = f"{source.stem}_{reason}_{timestamp}{source.suffix}"
        else:
            name = f"{source.stem}_{timestamp}{source.suffix}"

        dest = self._subdir(source.name) / name
        try:
            shutil.copy2(source, dest)
        except OSError as exc:
            raise StorageError(f"创建备份失败: {source}", detail=str(exc)) from exc

        info = self._info_from_path(dest)
        logger.info("已创建备份: %s", get_path_manager().relative(dest))
        self._prune_dir(dest.parent, self.max_backups)
        return info

    def backup_database(self) -> BackupInfo | None:
        """备份 SQLite 数据库文件 (使用在线备份 API, 兼容 WAL 模式).

        Returns:
            备份信息; 数据库不存在时返回 None, 失败时抛 :class:`StorageError`.
        """
        db_path = get_path_manager().db
        if not db_path.is_file():
            logger.warning("数据库文件不存在, 无需备份: %s", db_path)
            return None

        timestamp = datetime.now().strftime(_TS_FORMAT)
        dest = self._subdir(db_path.name) / f"{db_path.stem}_{timestamp}{db_path.suffix}"
        try:
            with closing(sqlite3.connect(db_path)) as src, closing(sqlite3.connect(dest)) as dst:
                src.backup(dst)
        except sqlite3.Error as exc:
            raise StorageError(f"备份数据库失败: {db_path}", detail=str(exc)) from exc

        info = self._info_from_path(dest)
        logger.info("已创建数据库备份: %s", get_path_manager().relative(dest))
        self._prune_dir(dest.parent, self.max_backups)
        return info

    # ------------------------------------------------------------------ #
    #  列举 / 恢复
    # ------------------------------------------------------------------ #
    def list_backups(self, filename: str) -> list[BackupInfo]:
        """列出指定源文件的所有备份 (按时间倒序)."""
        sub = self.backup_dir / self._subdir_name(filename)
        if not sub.is_dir():
            return []

        prefix = Path(filename).stem
        infos: list[BackupInfo] = []
        for entry in sub.iterdir():
            if not entry.is_file() or not entry.name.startswith(prefix):
                continue
            try:
                infos.append(self._info_from_path(entry))
            except OSError as exc:
                logger.warning("读取备份信息失败 %s: %s", entry, exc)

        infos.sort(key=lambda info: info.created_at, reverse=True)
        return infos

    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """从备份恢复文件; 恢复前会先临时备份当前目标文件.

        Returns:
            备份不存在时返回 False; 恢复成功返回 True, 写入失败抛 :class:`StorageError`.
        """
        backup_path = Path(backup_path)
        target_path = Path(target_path)
        if not backup_path.is_file():
            logger.error("备份文件不存在: %s", backup_path)
            return False

        try:
            if target_path.exists():
                timestamp = datetime.now().strftime(_TS_FORMAT)
                safety = target_path.with_name(f"{target_path.name}.before_restore_{timestamp}")
                shutil.copy2(target_path, safety)
                logger.info("当前文件已临时备份到: %s", safety)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)
        except OSError as exc:
            raise StorageError(
                f"恢复备份失败: {backup_path} -> {target_path}", detail=str(exc)
            ) from exc

        logger.info("已从备份恢复: %s -> %s", backup_path, target_path)
        return True

    # ------------------------------------------------------------------ #
    #  清理
    # ------------------------------------------------------------------ #
    def prune(self, max_backups: int) -> int:
        """对每个源文件仅保留最近 ``max_backups`` 份备份.

        Returns:
            实际删除的备份文件数量.
        """
        removed = 0
        for sub in self.backup_dir.iterdir():
            if sub.is_dir():
                removed += self._prune_dir(sub, max_backups)
        return removed

    @staticmethod
    def _prune_dir(subdir: Path, max_backups: int) -> int:
        """清理单个备份子目录, 保留最近 ``max_backups`` 份."""
        try:
            files = sorted(
                (p for p in subdir.iterdir() if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError as exc:
            logger.warning("清理旧备份失败 %s: %s", subdir, exc)
            return 0

        removed = 0
        for old in files[max(max_backups, 0) :]:
            try:
                old.unlink()
            except OSError as exc:
                logger.warning("删除旧备份失败 %s: %s", old, exc)
                continue
            removed += 1
            logger.info("已清理旧备份: %s", old)
        return removed


#: 全局备份管理器实例
backup_manager = BackupManager()


__all__ = ["BackupInfo", "BackupManager", "backup_manager"]
