"""米游社新闻 SQLite 存储层（E2）

按游戏分表（news_genshin / news_zzz / news_starrail），主键 iInfoId，
支持 upsert 与去重查询。

设计取舍（依据优化实施计划 E2 + 提问流程结论）：
- 不迁移历史 .txt 数据，只对新抓取写入 SQLite；
- .txt 仍作为只读去重源保留（由 fetchers/news/base.py 合并到 existing_urls）；
- 表结构与 core.api_client 返回的 item 字段一致，可直接 upsert。

用法：
    with NewsStorage() as store:
        store.upsert_items("genshin", items)
        existing = store.get_existing_urls("genshin")
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Set

from utils.logger import get_module_logger

logger = get_module_logger(__name__)

# 支持的游戏及对应表名
GAME_TABLES = {
    "genshin": "news_genshin",
    "zzz": "news_zzz",
    "starrail": "news_starrail",
}

_DEFAULT_DB_PATH = Path("data") / "news.db"


class NewsStorage:
    """米游社新闻 SQLite 存储"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.debug(f"NewsStorage 已连接: {self.db_path}")

    def _init_schema(self) -> None:
        """为每个游戏建表（主键 iInfoId，与 api_client item 字段一致）"""
        for game, table in GAME_TABLES.items():
            self._conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    iInfoId       TEXT PRIMARY KEY,
                    sTitle        TEXT,
                    date          TEXT,
                    sCategoryName TEXT,
                    sIntro        TEXT,
                    poster_url    TEXT,
                    url           TEXT,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        self._conn.commit()

    @staticmethod
    def _table(game: str) -> str:
        if game not in GAME_TABLES:
            raise ValueError(f"不支持的游戏标识: {game}（支持: {list(GAME_TABLES)}）")
        return GAME_TABLES[game]

    def upsert_items(self, game: str, items: List[dict]) -> int:
        """批量 upsert 新闻

        使用 INSERT OR IGNORE：已存在的 iInfoId 跳过（去重）。
        返回本次新增条数。
        """
        table = self._table(game)
        new_count = 0
        for it in items:
            cur = self._conn.execute(
                f"""INSERT OR IGNORE INTO {table}
                (iInfoId, sTitle, date, sCategoryName, sIntro, poster_url, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    it.get("iInfoId"),
                    it.get("sTitle"),
                    it.get("date"),
                    it.get("sCategoryName"),
                    it.get("sIntro"),
                    it.get("poster_url"),
                    it.get("url"),
                ),
            )
            new_count += cur.rowcount
        self._conn.commit()
        logger.info(f"[{game}] 写入 {len(items)} 条，新增 {new_count} 条（去重跳过 {len(items) - new_count} 条）")
        return new_count

    def get_existing_urls(self, game: str) -> Set[str]:
        """返回该游戏已存的 URL 集合（供增量去重合并到 existing_urls）"""
        table = self._table(game)
        rows = self._conn.execute(f"SELECT url FROM {table}").fetchall()
        return {r["url"] for r in rows if r["url"]}

    def get_existing_ids(self, game: str) -> Set[str]:
        """返回该游戏已存的 iInfoId 集合"""
        table = self._table(game)
        rows = self._conn.execute(f"SELECT iInfoId FROM {table}").fetchall()
        return {r["iInfoId"] for r in rows}

    def count(self, game: str) -> int:
        """返回该游戏已存条数"""
        table = self._table(game)
        return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def count_all(self) -> dict:
        """返回各游戏条数 {game: count}"""
        return {game: self.count(game) for game in GAME_TABLES}

    def get_all_items(self, game: str) -> List[dict]:
        """返回该游戏全部新闻（按日期倒序），供 Excel 导出等读取"""
        table = self._table(game)
        rows = self._conn.execute(
            f"SELECT iInfoId, sTitle, date, sCategoryName, sIntro, poster_url, url "
            f"FROM {table} ORDER BY date DESC"
        ).fetchall()
        return [
            {
                "iInfoId": r["iInfoId"],
                "sTitle": r["sTitle"],
                "date": r["date"],
                "sCategoryName": r["sCategoryName"],
                "sIntro": r["sIntro"],
                "poster_url": r["poster_url"],
                "url": r["url"],
            }
            for r in rows
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "NewsStorage":
        return self

    def __exit__(self, *args) -> None:
        self.close()
