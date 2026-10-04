"""
备份管理器
支持在数据更新前自动备份旧数据，并支持恢复
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class BackupInfo:
    """备份信息"""
    filename: str
    filepath: str
    created_at: datetime
    size: int


class BackupManager:
    """备份管理器，负责数据的备份和恢复"""

    def __init__(self, backup_dir: str = "data/backups", max_backups: int = 10):
        """
        初始化备份管理器

        Args:
            backup_dir: 备份目录路径
            max_backups: 最大备份数量，超过则自动清理最旧的备份
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """确保备份目录存在"""
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

    def _get_backup_subdir(self, filename: str) -> str:
        """获取指定文件的备份子目录"""
        base_name = Path(filename).stem
        subdir = os.path.join(self.backup_dir, base_name)
        Path(subdir).mkdir(parents=True, exist_ok=True)
        return subdir

    def create_backup(self, source_file: str, backup_name: Optional[str] = None) -> Optional[str]:
        """
        创建文件备份

        Args:
            source_file: 源文件路径
            backup_name: 自定义备份名称（可选），默认使用时间戳

        Returns:
            备份文件路径，失败返回 None
        """
        if not os.path.exists(source_file):
            print(f"[INFO] 源文件不存在，无需备份: {source_file}")
            return None

        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            source_filename = os.path.basename(source_file)
            base_name = Path(source_filename).stem
            ext = Path(source_filename).suffix

            if backup_name:
                backup_filename = f"{base_name}_{backup_name}{ext}"
            else:
                backup_filename = f"{base_name}_{timestamp}{ext}"

            # 创建备份子目录
            backup_subdir = self._get_backup_subdir(source_filename)
            backup_path = os.path.join(backup_subdir, backup_filename)

            # 复制文件
            shutil.copy2(source_file, backup_path)
            print(f"[OK] 已创建备份: {backup_path}")

            # 清理旧备份
            self._cleanup_old_backups(backup_subdir, base_name)

            return backup_path

        except Exception as e:
            print(f"[ERROR] 创建备份失败: {e}")
            return None

    def _cleanup_old_backups(self, backup_subdir: str, base_name: str) -> None:
        """清理旧备份，只保留最新的 max_backups 个"""
        try:
            # 获取所有备份文件
            backups = []
            for file in os.listdir(backup_subdir):
                if file.startswith(base_name):
                    filepath = os.path.join(backup_subdir, file)
                    stat = os.stat(filepath)
                    backups.append((filepath, stat.st_mtime))

            # 按修改时间排序（最新的在前）
            backups.sort(key=lambda x: x[1], reverse=True)

            # 删除多余的旧备份
            if len(backups) > self.max_backups:
                for filepath, _ in backups[self.max_backups:]:
                    os.remove(filepath)
                    print(f"[INFO] 已清理旧备份: {filepath}")

        except Exception as e:
            print(f"[WARN] 清理旧备份失败: {e}")

    def list_backups(self, filename: str) -> List[BackupInfo]:
        """
        列出指定文件的所有备份

        Args:
            filename: 原始文件名

        Returns:
            备份信息列表，按时间倒序排列
        """
        backup_subdir = self._get_backup_subdir(filename)
        backups = []

        try:
            base_name = Path(filename).stem
            for file in os.listdir(backup_subdir):
                if file.startswith(base_name):
                    filepath = os.path.join(backup_subdir, file)
                    stat = os.stat(filepath)
                    created_at = datetime.fromtimestamp(stat.st_mtime)
                    backups.append(BackupInfo(
                        filename=file,
                        filepath=filepath,
                        created_at=created_at,
                        size=stat.st_size
                    ))

            # 按时间倒序排列
            backups.sort(key=lambda x: x.created_at, reverse=True)

        except Exception as e:
            print(f"[ERROR] 列出备份失败: {e}")

        return backups

    def restore_backup(self, backup_path: str, target_path: str) -> bool:
        """
        从备份恢复文件

        Args:
            backup_path: 备份文件路径
            target_path: 目标文件路径

        Returns:
            是否恢复成功
        """
        if not os.path.exists(backup_path):
            print(f"[ERROR] 备份文件不存在: {backup_path}")
            return False

        try:
            # 如果目标文件存在，先备份它
            if os.path.exists(target_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_backup = f"{target_path}.before_restore_{timestamp}"
                shutil.copy2(target_path, temp_backup)
                print(f"[INFO] 当前文件已临时备份到: {temp_backup}")

            # 恢复备份
            shutil.copy2(backup_path, target_path)
            print(f"[OK] 已从备份恢复: {backup_path} -> {target_path}")
            return True

        except Exception as e:
            print(f"[ERROR] 恢复备份失败: {e}")
            return False

    def get_latest_backup(self, filename: str) -> Optional[str]:
        """
        获取指定文件的最新备份路径

        Args:
            filename: 原始文件名

        Returns:
            最新备份文件路径，不存在返回 None
        """
        backups = self.list_backups(filename)
        if backups:
            return backups[0].filepath
        return None

    def get_backup_size_mb(self, filename: str) -> float:
        """
        获取指定文件备份的总大小（MB）

        Args:
            filename: 原始文件名

        Returns:
            备份总大小（MB）
        """
        backups = self.list_backups(filename)
        total_size = sum(b.size for b in backups)
        return total_size / (1024 * 1024)


# 全局备份管理器实例
backup_manager = BackupManager()
