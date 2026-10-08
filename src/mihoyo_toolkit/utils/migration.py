"""数据迁移工具.

将旧项目 (v1) 的 ``data/`` 目录结构迁移到新架构的目录与命名规范:

* HTML 文件按新命名规范重命名 (如 ``news_page.html`` -> ``genshin_news.html``).
* TXT 文件迁移到新的结果目录.
* 若存在旧 ``config.json``, 仅提示用户手工迁移为 ``config.toml``.

迁移源通过环境变量 ``MIHOYO_LEGACY_DIR`` 指定; 未设置时视为无需迁移.
迁移采用 "复制" 而非 "移动", 保留源文件直至确认成功.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from ..core.config import get_settings
from ..core.exceptions import MihoyoError
from ..core.paths import get_path_manager
from .backup_manager import backup_manager
from .logger import get_module_logger

logger = get_module_logger("migration")

#: 旧文件名 -> 新文件名的显式映射
_LEGACY_NAME_MAP: dict[str, str] = {
    "news_page.html": "genshin_news.html",
    "news.txt": "genshin_news.txt",
}

#: 旧顶层目录名 -> PathManager 目录属性名
_DIR_MAP: dict[str, str] = {
    "html": "html",
    "data": "results",
    "results": "results",
    "images": "images",
    "models": "models",
}

#: 参与迁移的文件后缀
_SUPPORTED_SUFFIXES = {".html", ".txt"}


class DataMigrationManager:
    """旧数据目录结构迁移管理器."""

    def __init__(self, legacy_dir: Path | None = None) -> None:
        self.paths = get_path_manager()
        env_dir = os.environ.get("MIHOYO_LEGACY_DIR")
        if legacy_dir is not None:
            self.legacy_dir: Path | None = Path(legacy_dir)
        elif env_dir:
            self.legacy_dir = Path(env_dir).expanduser()
        else:
            self.legacy_dir = None
        #: 已迁移的 (源路径, 目标路径) 记录
        self.migrated_files: list[tuple[Path, Path]] = []

    # ------------------------------------------------------------------ #
    #  路径解析
    # ------------------------------------------------------------------ #
    @property
    def _legacy_data(self) -> Path | None:
        """旧数据根目录: 优先 ``<legacy>/data``, 否则 legacy 目录本身."""
        if self.legacy_dir is None or not self.legacy_dir.is_dir():
            return None
        nested = self.legacy_dir / "data"
        return nested if nested.is_dir() else self.legacy_dir

    def _legacy_config(self) -> Path | None:
        """返回旧 ``config.json`` 路径 (存在时)."""
        if self.legacy_dir is None or not self.legacy_dir.is_dir():
            return None
        candidates = (
            self.legacy_dir / "config.json",
            self.legacy_dir / "data" / "config.json",
        )
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def warn_legacy_config(self) -> Path | None:
        """若存在旧 ``config.json`` 则记录提示, 返回其路径."""
        config = self._legacy_config()
        if config is not None:
            logger.warning("检测到旧配置文件 %s, 请手工迁移为 config.toml", config)
        return config

    @staticmethod
    def _new_name(name: str) -> str:
        """按新命名规范转换文件名."""
        mapped = _LEGACY_NAME_MAP.get(name.lower())
        if mapped is not None:
            return mapped
        stem, dot, suffix = name.rpartition(".")
        if dot and suffix.lower() == "html" and stem.lower().endswith("_page"):
            return f"{stem[:-5]}_news.html"
        return name

    def _target_path(self, src: Path) -> Path:
        """计算旧文件在新目录结构中的目标路径."""
        root = self._legacy_data
        if root is None:
            raise MihoyoError("未配置旧数据目录")

        rel = src.relative_to(root)
        parts = list(rel.parts)
        name = self._new_name(src.name)
        first = parts[0].lower()

        roots: dict[str, Path] = {
            "html": self.paths.html,
            "results": self.paths.results,
            "images": self.paths.images,
            "models": self.paths.models,
        }

        if len(parts) > 1 and first in _DIR_MAP:
            target_root = roots[_DIR_MAP[first]]
            sub = Path(*parts[1:-1])
        else:
            is_html = src.suffix.lower() == ".html"
            target_root = self.paths.html if is_html else self.paths.results
            sub = Path(*parts[:-1])

        return target_root / sub / name

    def _iter_legacy_files(self) -> list[Path]:
        """递归列出旧数据目录中待迁移的 HTML / TXT 文件."""
        root = self._legacy_data
        if root is None:
            return []
        return sorted(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES
        )

    # ------------------------------------------------------------------ #
    #  迁移
    # ------------------------------------------------------------------ #
    def needs_migration(self) -> bool:
        """判断是否仍需迁移文件 (幂等: 文件迁移完成后返回 False)."""
        if self._legacy_data is None:
            return False
        return any(not self._target_path(src).exists() for src in self._iter_legacy_files())

    def run_migration(self) -> dict[str, Any]:
        """执行数据迁移.

        Returns:
            结果字典, 包含 ``success`` / ``migrated_files`` / ``skipped_files`` / ``errors``.
        """
        result: dict[str, Any] = {
            "success": True,
            "migrated_files": [],
            "skipped_files": [],
            "errors": [],
        }

        if not self.needs_migration():
            logger.info("无需数据迁移")
            return result

        logger.info("开始数据迁移 (旧目录: %s)", self.legacy_dir)

        config = self.warn_legacy_config()
        if config is not None:
            result["skipped_files"].append(self.paths.relative(config))

        backup_enabled = get_settings().backup.enabled
        for src in self._iter_legacy_files():
            dest = self._target_path(src)
            if dest.exists():
                result["skipped_files"].append(self.paths.relative(src))
                logger.info("目标已存在, 跳过: %s", dest)
                continue

            try:
                if backup_enabled:
                    backup_manager.backup_file(src, reason="migration")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            except (OSError, MihoyoError) as exc:
                result["success"] = False
                result["errors"].append(f"{src}: {exc}")
                logger.error("迁移失败 %s: %s", src, exc)
                continue

            result["migrated_files"].append(
                f"{self.paths.relative(src)} -> {self.paths.relative(dest)}"
            )
            self.migrated_files.append((src, dest))
            logger.info("已迁移: %s -> %s", src, dest)

        logger.info("数据迁移完成, 共迁移 %d 个文件", len(result["migrated_files"]))
        return result


def check_and_migrate() -> None:
    """检查并按需执行迁移 (幂等, 异常不外抛, 仅记录日志)."""
    try:
        manager = DataMigrationManager()
        if manager.needs_migration():
            manager.run_migration()
        else:
            manager.warn_legacy_config()
    except Exception:
        # 迁移为后台尽力而为的操作, 不应中断主流程
        logger.exception("数据迁移检查失败")


__all__ = ["DataMigrationManager", "check_and_migrate"]
