"""图鉴图片链接提取（SQLite → TXT）。

抓取层已把图鉴图片写入 ``images`` 表，提取层只读库并导出为 v1 的 TXT 行格式::

    序号-名称-[图片URL]
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..core.exceptions import StorageError
from ..core.models import ImageItem
from ..core.paths import get_path_manager
from ..core.storage import Storage
from ..utils.logger import get_module_logger

logger = get_module_logger("extractors.images")

_TOPIC = "image_urls"


class ImageExtractor:
    """从 ``images`` 表导出图片链接 TXT。"""

    def __init__(self, topic: str = _TOPIC, *, db_path: str | Path | None = None) -> None:
        self.topic = topic
        self._db_path = db_path

    @property
    def output_path(self) -> Path:
        """导出目标：``data/results/image_urls.txt``。"""
        return get_path_manager().results / f"{self.topic}.txt"

    def load_images(self) -> list[ImageItem]:
        """从 SQLite 读取全部图片链接。"""
        with Storage(self._db_path) as store:
            try:
                rows = (
                    store.connect()
                    .execute("SELECT character_id, name, image_url FROM images ORDER BY id")
                    .fetchall()
                )
            except sqlite3.Error as exc:
                raise StorageError("读取 images 表失败", detail=str(exc)) from exc
        return [
            ImageItem(
                character_id=row["character_id"],
                name=row["name"],
                image_url=row["image_url"],
            )
            for row in rows
        ]

    def extract_image_urls(self, *, limit: int | None = None) -> list[ImageItem]:
        """读取图片链接列表（``limit`` 可选）。"""
        items = self.load_images()
        if limit is not None:
            items = items[:limit]
        logger.info("读取图片链接 %d 条", len(items))
        return items

    def save_image_data(self, items: list[ImageItem]) -> Path:
        """写出 TXT，返回输出路径。"""
        path_manager = get_path_manager()
        path_manager.results.mkdir(parents=True, exist_ok=True)
        lines = [
            f"{index:04d}-{item.name}-[{item.image_url}]" for index, item in enumerate(items, 1)
        ]
        self.output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(
            "已导出 %d 个图片链接 → %s", len(items), path_manager.relative(self.output_path)
        )
        return self.output_path


def run_extract_images() -> None:
    """读取 ``images`` 表并导出 ``data/results/image_urls.txt``。"""
    extractor = ImageExtractor()
    items = extractor.extract_image_urls()
    if not items:
        logger.warning("images 表暂无数据，跳过导出（请先抓取角色图鉴）")
        return
    extractor.save_image_data(items)


__all__ = ["ImageExtractor", "run_extract_images"]
