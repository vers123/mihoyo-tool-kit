"""统一 SQLite 存储层。

取代原项目的「新闻进 SQLite + 其他写 TXT」混合方案，所有抓取结果统一落库。

设计要点：

* 单文件数据库（默认 ``data/toolkit.db``），WAL 模式提升并发读写。
* ``news`` 表以 ``(game, url)`` 唯一索引实现去重与幂等 upsert。
* 其余实体（posts / weibo / tutorial / images）各有独立表，schema 稳定。
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .exceptions import StorageError
from .models import ImageItem, NewsItem, PostItem, TutorialItem, WeiboItem
from .paths import get_path_manager

_SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    game          TEXT    NOT NULL,
    info_id       INTEGER NOT NULL,
    title         TEXT    NOT NULL DEFAULT '',
    start_time    TEXT    NOT NULL DEFAULT '',
    category      TEXT    NOT NULL DEFAULT '',
    intro         TEXT    NOT NULL DEFAULT '',
    poster_url    TEXT    NOT NULL DEFAULT '',
    url           TEXT    NOT NULL,
    raw           TEXT    NOT NULL DEFAULT '{}',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (game, url)
);
CREATE INDEX IF NOT EXISTS idx_news_game_time ON news (game, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_news_info_id   ON news (game, info_id);

CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id     TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT '',
    url         TEXT    NOT NULL DEFAULT '',
    content     TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS weibo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id     TEXT    NOT NULL UNIQUE,
    text        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT '',
    url         TEXT    NOT NULL DEFAULT '',
    reposts     INTEGER NOT NULL DEFAULT 0,
    comments    INTEGER NOT NULL DEFAULT 0,
    attitudes   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tutorial (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  TEXT    NOT NULL,
    name          TEXT    NOT NULL DEFAULT '',
    lang          TEXT    NOT NULL DEFAULT '',
    UNIQUE (character_id, lang)
);

CREATE TABLE IF NOT EXISTS images (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  TEXT    NOT NULL DEFAULT '',
    name          TEXT    NOT NULL DEFAULT '',
    image_url     TEXT    NOT NULL UNIQUE
);
"""


class Storage:
    """SQLite 存储门面。

    作为上下文管理器使用::

        with Storage() as store:
            new = store.upsert_news("genshin", items)
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else get_path_manager().db
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------ #
    #  连接管理
    # ------------------------------------------------------------------ #
    @property
    def db_path(self) -> Path:
        return self._db_path

    def connect(self) -> sqlite3.Connection:
        """建立连接并初始化 schema（幂等）。"""
        if self._conn is not None:
            return self._conn
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(_SCHEMA)
            conn.commit()
        except sqlite3.Error as exc:  # pragma: no cover - 环境相关
            raise StorageError(f"初始化数据库失败: {self._db_path}", detail=str(exc)) from exc
        self._conn = conn
        return conn

    def close(self) -> None:
        """关闭连接。"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> Storage:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = self.connect()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise StorageError("数据库操作失败", detail=str(exc)) from exc
        finally:
            cur.close()

    # ------------------------------------------------------------------ #
    #  新闻
    # ------------------------------------------------------------------ #
    def upsert_news(self, game: str, items: Iterable[NewsItem]) -> int:
        """批量写入新闻，返回新增条数（按 (game, url) 去重）。"""
        rows = [
            (
                game,
                item.iInfoId,
                item.sTitle,
                item.dtStartTime,
                item.sCategoryName,
                item.sIntro,
                item.poster_url,
                item.url,
                json.dumps(item.raw, ensure_ascii=False),
            )
            for item in items
        ]
        if not rows:
            return 0
        before = self.count_news(game)
        with self._cursor() as cur:
            cur.executemany(
                """
                INSERT OR IGNORE INTO news
                    (game, info_id, title, start_time, category, intro, poster_url, url, raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return self.count_news(game) - before

    def get_existing_urls(self, game: str) -> set[str]:
        """获取指定游戏已存在的 URL 集合（用于增量抓取终止判断）。"""
        with self._cursor() as cur:
            cur.execute("SELECT url FROM news WHERE game = ?", (game,))
            return {row["url"] for row in cur.fetchall()}

    def get_existing_info_ids(self, game: str) -> set[int]:
        """获取指定游戏已存在的 iInfoId 集合。"""
        with self._cursor() as cur:
            cur.execute("SELECT info_id FROM news WHERE game = ?", (game,))
            return {row["info_id"] for row in cur.fetchall()}

    def count_news(self, game: str | None = None) -> int:
        """统计新闻条数；game 为 None 时统计全部。"""
        with self._cursor() as cur:
            if game is None:
                cur.execute("SELECT COUNT(*) AS n FROM news")
            else:
                cur.execute("SELECT COUNT(*) AS n FROM news WHERE game = ?", (game,))
            return int(cur.fetchone()["n"])

    def count_all(self) -> dict[str, int]:
        """按游戏统计新闻条数，返回 {game: count}。"""
        with self._cursor() as cur:
            cur.execute("SELECT game, COUNT(*) AS n FROM news GROUP BY game")
            return {row["game"]: int(row["n"]) for row in cur.fetchall()}

    def query_news(
        self,
        game: str | None = None,
        *,
        limit: int | None = None,
        ascending: bool = False,
    ) -> list[NewsItem]:
        """查询新闻，默认按时间倒序。"""
        order = "ASC" if ascending else "DESC"
        sql = "SELECT * FROM news"
        params: list[Any] = []
        if game is not None:
            sql += " WHERE game = ?"
            params.append(game)
        sql += f" ORDER BY start_time {order}, info_id {order}"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_news(row) for row in cur.fetchall()]

    @staticmethod
    def _row_to_news(row: sqlite3.Row) -> NewsItem:
        try:
            raw = json.loads(row["raw"]) if row["raw"] else {}
        except json.JSONDecodeError:
            raw = {}
        return NewsItem(
            game=row["game"],
            iInfoId=row["info_id"],
            sTitle=row["title"],
            dtStartTime=row["start_time"],
            sCategoryName=row["category"],
            sIntro=row["intro"],
            poster_url=row["poster_url"],
            url=row["url"],
            raw=raw,
        )

    # ------------------------------------------------------------------ #
    #  通用实体写入（posts / weibo / tutorial / images）
    # ------------------------------------------------------------------ #
    def upsert_posts(self, items: Iterable[PostItem]) -> int:
        """写入米游社用户发帖，返回新增条数。"""
        rows = [(i.post_id, i.title, i.created_at, i.url, i.content) for i in items]
        return self._upsert_generic(
            "INSERT OR IGNORE INTO posts (post_id, title, created_at, url, content)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
            "posts",
        )

    def upsert_weibo(self, items: Iterable[WeiboItem]) -> int:
        """写入微博帖子，返回新增条数。"""
        rows = [
            (i.post_id, i.text, i.created_at, i.url, i.reposts, i.comments, i.attitudes)
            for i in items
        ]
        return self._upsert_generic(
            "INSERT OR IGNORE INTO weibo"
            " (post_id, text, created_at, url, reposts, comments, attitudes)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
            "weibo",
        )

    def upsert_tutorial(self, items: Iterable[TutorialItem]) -> int:
        """写入教程角色数据，返回新增条数。"""
        rows = [(i.character_id, i.name, i.lang) for i in items]
        return self._upsert_generic(
            "INSERT OR IGNORE INTO tutorial (character_id, name, lang) VALUES (?, ?, ?)",
            rows,
            "tutorial",
        )

    def upsert_images(self, items: Iterable[ImageItem]) -> int:
        """写入图鉴图片链接，返回新增条数。"""
        rows = [(i.character_id, i.name, i.image_url) for i in items]
        return self._upsert_generic(
            "INSERT OR IGNORE INTO images (character_id, name, image_url) VALUES (?, ?, ?)",
            rows,
            "images",
        )

    def query_posts(self, *, limit: int | None = None, ascending: bool = False) -> list[PostItem]:
        """查询米游社用户发帖，默认按时间倒序。"""
        order = "ASC" if ascending else "DESC"
        sql = f"SELECT * FROM posts ORDER BY created_at {order}"
        if limit is not None:
            sql += " LIMIT ?"
        with self._cursor() as cur:
            cur.execute(sql, (limit,) if limit is not None else ())
            return [
                PostItem(
                    post_id=row["post_id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    url=row["url"],
                    content=row["content"],
                )
                for row in cur.fetchall()
            ]

    def query_weibo(self, *, limit: int | None = None, ascending: bool = False) -> list[WeiboItem]:
        """查询微博帖子，默认按时间倒序。"""
        order = "ASC" if ascending else "DESC"
        sql = f"SELECT * FROM weibo ORDER BY created_at {order}"
        if limit is not None:
            sql += " LIMIT ?"
        with self._cursor() as cur:
            cur.execute(sql, (limit,) if limit is not None else ())
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
                for row in cur.fetchall()
            ]

    def query_images(self) -> list[ImageItem]:
        """查询图鉴图片链接。"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM images ORDER BY character_id, id")
            return [
                ImageItem(
                    character_id=row["character_id"],
                    name=row["name"],
                    image_url=row["image_url"],
                )
                for row in cur.fetchall()
            ]

    def get_existing_post_ids(self) -> set[str]:
        """获取已存在的发帖 ID 集合（用于增量终止判断）。"""
        with self._cursor() as cur:
            cur.execute("SELECT post_id FROM posts")
            return {row["post_id"] for row in cur.fetchall()}

    def get_existing_weibo_ids(self) -> set[str]:
        """获取已存在的微博 ID 集合（用于增量终止判断）。"""
        with self._cursor() as cur:
            cur.execute("SELECT post_id FROM weibo")
            return {row["post_id"] for row in cur.fetchall()}

    def _upsert_generic(self, sql: str, rows: list[tuple[Any, ...]], table: str) -> int:
        if not rows:
            return 0
        before = self._count_table(table)
        with self._cursor() as cur:
            cur.executemany(sql, rows)
        return self._count_table(table) - before

    def _count_table(self, table: str, where: str = "", params: tuple[Any, ...] = ()) -> int:
        # table 仅来自内部常量，无注入风险
        sql = f"SELECT COUNT(*) AS n FROM {table}"
        if where:
            sql += f" WHERE {where}"
        with self._cursor() as cur:
            cur.execute(sql, params)
            return int(cur.fetchone()["n"])

    def count_table(self, table: str) -> int:
        """统计任意已知表的行数。"""
        if table not in {"news", "posts", "weibo", "tutorial", "images"}:
            raise StorageError(f"未知表名: {table}")
        return self._count_table(table)

    # ------------------------------------------------------------------ #
    #  维护
    # ------------------------------------------------------------------ #
    def vacuum(self) -> None:
        """压缩数据库文件。"""
        conn = self.connect()
        conn.execute("VACUUM")
        conn.commit()

    def clear(self, game: str | None = None) -> int:
        """清空新闻（可指定 game），返回删除条数。"""
        before = self.count_news(game)
        with self._cursor() as cur:
            if game is None:
                cur.execute("DELETE FROM news")
            else:
                cur.execute("DELETE FROM news WHERE game = ?", (game,))
        return before


__all__ = ["Storage"]
