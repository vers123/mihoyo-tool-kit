"""米游社用户发帖提取（SQLite → TXT）。

抓取层已把用户发帖写入 ``posts`` 表，提取层只读库、按时间倒序并导出为 v1
的 TXT 行格式（条目间空行分隔）::

    序号-标题-[YYYY-MM-DD HH:MM:SS](URL)

增量语义：读库即全量，``incremental`` 仅为兼容保留。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..core.exceptions import StorageError
from ..core.models import PostItem
from ..core.paths import get_path_manager
from ..core.storage import Storage
from ..utils.logger import get_module_logger

logger = get_module_logger("extractors.posts")

_TOPIC = "posts"

#: 导出子目录（相对 ``data/results``）
SUBDIR = "user"


class PostExtractor:
    """从 ``posts`` 表导出用户发帖 TXT。"""

    def __init__(self, topic: str = _TOPIC, *, db_path: str | Path | None = None) -> None:
        self.topic = topic
        self._db_path = db_path

    @property
    def output_path(self) -> Path:
        """导出目标：``data/results/{SUBDIR}/{topic}.txt``。"""
        return get_path_manager().results / SUBDIR / f"{self.topic}.txt"

    def load_posts(self) -> list[PostItem]:
        """从 SQLite 读取全部帖子（按创建时间倒序）。"""
        with Storage(self._db_path) as store:
            try:
                rows = (
                    store.connect()
                    .execute(
                        "SELECT post_id, title, created_at, url, content FROM posts"
                        " ORDER BY created_at DESC, id DESC"
                    )
                    .fetchall()
                )
            except sqlite3.Error as exc:
                raise StorageError("读取 posts 表失败", detail=str(exc)) from exc
        return [
            PostItem(
                post_id=row["post_id"],
                title=row["title"],
                created_at=row["created_at"],
                url=row["url"],
                content=row["content"],
            )
            for row in rows
        ]

    def extract_posts(
        self, incremental: bool = False, *, limit: int | None = None
    ) -> list[PostItem]:
        """读取帖子列表。

        Args:
            incremental: 兼容参数（保留），读库即全量。
            limit: 可选，仅取前 N 条。
        """
        items = self.load_posts()
        if limit is not None:
            items = items[:limit]
        logger.info("读取帖子 %d 条（incremental=%s）", len(items), incremental)
        return items

    def save_post_data(self, items: list[PostItem]) -> Path:
        """写出 TXT，返回输出路径。"""
        path_manager = get_path_manager()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"{index:04d}-{item.title}-[{item.created_at}]({item.url})"
            for index, item in enumerate(items, 1)
        ]
        self.output_path.write_text("\n\n".join(lines), encoding="utf-8")
        logger.info("已导出 %d 条帖子 → %s", len(items), path_manager.relative(self.output_path))
        return self.output_path


def run_extract_posts(incremental: bool = False) -> None:
    """读取 ``posts`` 表并导出 ``data/results/user/posts.txt``。"""
    extractor = PostExtractor()
    items = extractor.extract_posts(incremental=incremental)
    if not items:
        logger.warning("posts 表暂无数据，跳过导出（请先抓取用户发帖）")
        return
    extractor.save_post_data(items)


__all__ = ["PostExtractor", "run_extract_posts"]
