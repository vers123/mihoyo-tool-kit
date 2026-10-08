"""
数据迁移工具
负责将旧版本的数据文件迁移到新的目录结构和命名规范

迁移内容：
- 原神新闻：news_page.html → genshin/news_genshin.html
- 原神新闻：news.txt → genshin/news_genshin.txt
"""

import os
import shutil
from typing import Dict, List, Tuple
from core.config_manager import config_manager
from utils.backup_manager import backup_manager


class DataMigrationManager:
    """数据迁移管理器"""

    def __init__(self):
        self.base_dir = config_manager.base_dir
        self.migration_config = config_manager.get("migration", {})
        self.migrated_files: List[Tuple[str, str]] = []  # (源路径, 目标路径)

    def needs_migration(self) -> bool:
        """检查是否需要进行数据迁移"""
        if not self.migration_config.get("enabled", True):
            return False

        # 检查原神旧文件是否存在
        old_files = self._get_genshin_old_files()
        for old_path, _ in old_files:
            if os.path.exists(old_path):
                return True

        return False

    def _get_genshin_old_files(self) -> List[Tuple[str, str]]:
        """获取原神旧文件和对应新路径的映射"""
        old_filenames = self.migration_config.get("genshin_old_filenames", {})
        old_html_name = old_filenames.get("html", "news_page.html")
        old_data_name = old_filenames.get("data", "news.txt")

        # 旧路径（根目录下的 html 和 data 目录）
        old_html_dir = config_manager.get_output_dir("html")
        old_data_dir = config_manager.get_output_dir("data")

        # 新路径（按游戏分子目录）
        new_html_dir = config_manager.get_news_output_dir("genshin", "html")
        new_data_dir = config_manager.get_news_output_dir("genshin", "data")

        site_config = config_manager.get_news_config("genshin")
        new_html_name = site_config.get("html_filename", "news_genshin.html")
        new_data_name = site_config.get("data_filename", "news_genshin.txt")

        return [
            (os.path.join(old_html_dir, old_html_name), os.path.join(new_html_dir, new_html_name)),
            (os.path.join(old_data_dir, old_data_name), os.path.join(new_data_dir, new_data_name)),
        ]

    def run_migration(self) -> Dict:
        """执行数据迁移

        Returns:
            迁移结果字典，包含：
            - success: 是否成功
            - migrated_files: 已迁移的文件列表
            - skipped_files: 跳过的文件列表
            - errors: 错误列表
        """
        result = {
            "success": True,
            "migrated_files": [],
            "skipped_files": [],
            "errors": []
        }

        if not self.needs_migration():
            print("[INFO] 无需数据迁移")
            return result

        print("\n" + "=" * 60)
        print("[MIGRATION] 开始数据迁移...")
        print("=" * 60)

        # 迁移原神旧文件
        for old_path, new_path in self._get_genshin_old_files():
            if not os.path.exists(old_path):
                result["skipped_files"].append(old_path)
                print(f"[SKIP] 源文件不存在: {old_path}")
                continue

            if os.path.exists(new_path):
                result["skipped_files"].append(old_path)
                print(f"[SKIP] 目标文件已存在: {new_path}")
                continue

            try:
                # 确保目标目录存在
                os.makedirs(os.path.dirname(new_path), exist_ok=True)

                # 先备份旧文件（如果备份功能开启）
                if config_manager.get("backup_settings.enabled", True):
                    try:
                        backup_manager.create_backup(old_path)
                        print(f"[BACKUP] 已备份源文件: {old_path}")
                    except Exception as e:
                        print(f"[WARN] 备份源文件失败: {e}")

                # 复制文件（保留源文件作为备份，直到确认迁移成功）
                shutil.copy2(old_path, new_path)
                result["migrated_files"].append((old_path, new_path))
                self.migrated_files.append((old_path, new_path))
                print(f"[OK] 已迁移: {os.path.basename(old_path)} → {os.path.basename(new_path)}")

            except Exception as e:
                result["success"] = False
                result["errors"].append(f"{old_path}: {e}")
                print(f"[ERROR] 迁移失败 {old_path}: {e}")

        print("=" * 60)
        if result["success"]:
            print(f"[MIGRATION] 数据迁移完成，共迁移 {len(result['migrated_files'])} 个文件")
        else:
            print(f"[MIGRATION] 数据迁移完成，{len(result['errors'])} 个错误")
        print("=" * 60 + "\n")

        return result

    def rollback_migration(self) -> bool:
        """回滚迁移（删除新创建的文件）"""
        if not self.migrated_files:
            print("[INFO] 没有可回滚的迁移")
            return True

        print("\n[ROLLBACK] 回滚数据迁移...")
        success = True

        for old_path, new_path in self.migrated_files:
            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                    print(f"[OK] 已删除: {new_path}")
            except Exception as e:
                print(f"[ERROR] 删除失败 {new_path}: {e}")
                success = False

        self.migrated_files = []
        return success


def run_migration() -> Dict:
    """运行数据迁移（便捷入口）"""
    manager = DataMigrationManager()
    return manager.run_migration()


def check_and_migrate() -> Dict:
    """检查并执行迁移（如果需要）"""
    manager = DataMigrationManager()
    if manager.needs_migration():
        return manager.run_migration()
    return {"success": True, "migrated_files": [], "skipped_files": [], "errors": []}


if __name__ == "__main__":
    run_migration()
