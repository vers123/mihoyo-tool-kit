"""新闻页面：同一个页面类通过 ``game`` 参数支持四站点。"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from ..models import NewsTableModel
from .base import BasePage

#: game key -> 显示名
GAME_NAMES: dict[str, str] = {
    "genshin": "原神",
    "genshin_en": "原神英文版",
    "zzz": "绝区零",
    "starrail": "星穹铁道",
}


class NewsPage(BasePage):
    """新闻抓取 / 提取页面（四站点共用）。

    Args:
        game: ``genshin`` / ``genshin_en`` / ``zzz`` / ``starrail``。
    """

    def __init__(self, game: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.game_name = GAME_NAMES.get(game, game)
        self.table_model = NewsTableModel(game, self)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(
            self.make_header(f"{self.game_name}新闻", "抓取新闻页面 HTML 并提取结构化数据")
        )

        self.btn_fetch = self.make_button("全量抓取", lambda: self._fetch(incremental=False))
        self.btn_incremental = self.make_button("增量抓取", lambda: self._fetch(incremental=True))
        self.btn_extract = self.make_button("提取数据", lambda: self._extract(incremental=False))
        self.btn_incremental_extract = self.make_button(
            "增量提取", lambda: self._extract(incremental=True)
        )
        self.register_buttons(
            self.btn_fetch,
            self.btn_incremental,
            self.btn_extract,
            self.btn_incremental_extract,
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        for button in (
            self.btn_fetch,
            self.btn_incremental,
            self.btn_extract,
            self.btn_incremental_extract,
        ):
            button_row.addWidget(button)
        button_row.addStretch()
        button_row.addWidget(self.btn_stop)
        layout.addLayout(button_row)

        layout.addWidget(self.progress)

        self.table = self.make_table(self.table_model)
        self.set_column_modes(
            self.table,
            {
                0: QHeaderView.ResizeMode.ResizeToContents,
                1: QHeaderView.ResizeMode.ResizeToContents,
                2: QHeaderView.ResizeMode.Stretch,
                3: QHeaderView.ResizeMode.ResizeToContents,
                4: QHeaderView.ResizeMode.ResizeToContents,
                5: QHeaderView.ResizeMode.Stretch,
                6: QHeaderView.ResizeMode.Interactive,
            },
        )
        layout.addWidget(self.table, 1)

        self.reload_table()

    # ------------------------------------------------------------------ #
    #  动作
    # ------------------------------------------------------------------ #
    def _fetch(self, *, incremental: bool) -> None:
        from ...scrapers import run_news

        mode = "增量" if incremental else "全量"
        game = self.game
        self.run_task(
            lambda: run_news(game, incremental=incremental),
            f"{mode}抓取{self.game_name}新闻",
        )

    def _extract(self, *, incremental: bool) -> None:
        from ...extractors import run_extract_news

        mode = "增量" if incremental else "全量"
        game = self.game
        self.run_task(
            lambda: run_extract_news(game, incremental=incremental),
            f"{mode}提取{self.game_name}新闻",
        )


__all__ = ["GAME_NAMES", "NewsPage"]
