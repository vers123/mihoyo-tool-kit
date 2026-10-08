"""微博提取（SQLite → TXT）。

抓取层已把微博写入 ``weibo`` 表，提取层只读库、按时间倒序并导出为 v1 的
TXT 行格式（条目间空行分隔）::

    序号-正文-[YYYY-MM-DD HH:MM:SS](URL)

增量语义：读库即全量，``incremental`` 仅为兼容保留。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..core.exceptions import StorageError
from ..core.models import WeiboItem
from ..core.paths import get_path_manager
from ..core.storage import Storage
from ..utils.logger import get_module_logger

logger = get_module_logger("extractors.weibo")

_TOPIC = "weibo"

#: 导出子目录（相对 ``data/results``）
SUBDIR = "weibo"


class WeiboExtractor:
    """从 ``weibo`` 表导出微博 TXT。"""

    def __init__(self, topic: str = _TOPIC, *, db_path: str | Path | None = None) -> None:
        self.topic = topic
        self._db_path = db_path

    @property
    def output_path(self) -> Path:
        """导出目标：``data/results/{SUBDIR}/{topic}.txt``。"""
        return get_path_manager().results / SUBDIR / f"{self.topic}.txt"

    def load_weibo(self) -> list[WeiboItem]:
        """从 SQLite 读取全部微博（按创建时间倒序）。"""
        with Storage(self._db_path) as store:
            try:
                rows = (
                    store.connect()
                    .execute(
                        "SELECT post_id, text, created_at, url, reposts, comments, attitudes"
                        " FROM weibo ORDER BY created_at DESC, id DESC"
                    )
                    .fetchall()
                )
            except sqlite3.Error as exc:
                raise StorageError("读取 weibo 表失败", detail=str(exc)) from exc
        return [
            WeiboItem(
                post_id=row["post_id"],
                text=row["text"],
                created_at=row["created_at"],
                url=row["url"],
                reposts=row["reposts"],
                comments=row["comments"],
                attitudes=row["attitudes"],
            )
            for row in rows
        ]

    def extract_weibo(
        self, incremental: bool = False, *, limit: int | None = None
    ) -> list[WeiboItem]:
        """读取微博列表。

        Args:
            incremental: 兼容参数（保留），读库即全量。
            limit: 可选，仅取前 N 条。
        """
        items = self.load_weibo()
        if limit is not None:
            items = items[:limit]
        logger.info("读取微博 %d 条（incremental=%s）", len(items), incremental)
        return items

    def save_weibo_data(self, items: list[WeiboItem]) -> Path:
        """写出 TXT，返回输出路径。"""
        path_manager = get_path_manager()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"{index:04d}-{item.text}-[{item.created_at}]({item.url})"
            for index, item in enumerate(items, 1)
        ]
        self.output_path.write_text("\n\n".join(lines), encoding="utf-8")
        logger.info("已导出 %d 条微博 → %s", len(items), path_manager.relative(self.output_path))
        return self.output_path


def run_extract_weibo(incremental: bool = False) -> None:
    """读取 ``weibo`` 表并导出 ``data/results/weibo/weibo.txt``。"""
    extractor = WeiboExtractor()
    items = extractor.extract_weibo(incremental=incremental)
    if not items:
        logger.warning("weibo 表暂无数据，跳过导出（请先抓取微博主页）")
        return
    extractor.save_weibo_data(items)


__all__ = ["WeiboExtractor", "run_extract_weibo"]
