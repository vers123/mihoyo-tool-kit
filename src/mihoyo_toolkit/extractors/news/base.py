"""新闻提取导出基类。

架构变化：抓取层已把四站点新闻直接写入 SQLite（``news`` 表），提取层不再是
「解析 HTML → 写 TXT」，而是「读库 → 排序 → 导出 TXT」。因此本基类只负责
从 :class:`~mihoyo_toolkit.core.storage.Storage` 读取并按原 7 字段格式落盘。

原 7 字段（对应 :class:`~mihoyo_toolkit.core.models.NewsItem`）：
``iInfoId / sTitle / dtStartTime / sCategoryName / sIntro / poster_url / url``

TXT 行格式（与 v1 保持一致）::

    序号-标题-[日期]-[分类]-[摘要]-[封面图URL]-(完整URL)

增量语义：由 SQLite 天然保证——读库即全量，``incremental`` 参数仅为向下兼容保留。
"""

from __future__ import annotations

from pathlib import Path

from ...core.config import NewsSiteSource, get_settings
from ...core.models import NewsItem
from ...core.paths import get_path_manager
from ...core.storage import Storage
from ...utils.logger import get_module_logger

logger = get_module_logger("extractors.news")


class GameNewsBaseExtractor:
    """四站点新闻提取导出基类。

    子类只需声明 :attr:`game`（如 ``game = "genshin"``），其余逻辑由此提供。
    """

    #: 子类覆盖：游戏 key（genshin / genshin_en / zzz / starrail）
    game: str = ""

    def __init__(self, game: str | None = None, *, db_path: str | Path | None = None) -> None:
        key = game or self.game
        if not key:
            raise ValueError("必须指定 game key")
        self.game = key
        self.site: NewsSiteSource = get_settings().sources.news.get_site(key)
        self._db_path = db_path

    # ------------------------------------------------------------------ #
    #  路径
    # ------------------------------------------------------------------ #
    @property
    def output_path(self) -> Path:
        """导出目标：``data/results/{game}_news.txt``。"""
        return get_path_manager().results / f"{self.game}_news.txt"

    # ------------------------------------------------------------------ #
    #  读取
    # ------------------------------------------------------------------ #
    def load_news(self, *, limit: int | None = None) -> list[NewsItem]:
        """从 SQLite 读取该站点新闻（默认按时间倒序）。"""
        with Storage(self._db_path) as store:
            items = store.query_news(self.game, limit=limit)
        logger.info("[%s] 从数据库读取 %d 条新闻", self.game, len(items))
        return items

    def extract_news(
        self, incremental: bool = False, *, limit: int | None = None
    ) -> list[NewsItem]:
        """读取新闻列表。

        Args:
            incremental: 兼容参数（保留）；合并/去重由 SQLite 唯一索引保证。
            limit: 可选，仅取前 N 条。
        """
        logger.debug("[%s] 提取新闻（incremental=%s）", self.game, incremental)
        return self.load_news(limit=limit)

    # ------------------------------------------------------------------ #
    #  导出
    # ------------------------------------------------------------------ #
    @staticmethod
    def format_line(index: int, item: NewsItem) -> str:
        """按 7 字段格式渲染单行。"""
        return (
            f"{index:04d}-{item.sTitle}"
            f"-[{item.dtStartTime}]"
            f"-[{item.sCategoryName}]"
            f"-[{item.sIntro}]"
            f"-[{item.poster_url}]"
            f"-({item.url})"
        )

    def save_news_data(self, items: list[NewsItem]) -> Path:
        """写出 TXT，返回输出路径。"""
        path_manager = get_path_manager()
        path_manager.results.mkdir(parents=True, exist_ok=True)
        lines = [self.format_line(index, item) for index, item in enumerate(items, 1)]
        self.output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(
            "[%s] 已导出 %d 条新闻 → %s",
            self.game,
            len(items),
            path_manager.relative(self.output_path),
        )
        return self.output_path

    def export(self, *, incremental: bool = False) -> Path | None:
        """读取并导出；无数据时返回 ``None``。"""
        items = self.extract_news(incremental=incremental)
        if not items:
            logger.warning("[%s] 数据库暂无新闻数据，跳过导出（请先抓取）", self.game)
            return None
        return self.save_news_data(items)


__all__ = ["GameNewsBaseExtractor"]
