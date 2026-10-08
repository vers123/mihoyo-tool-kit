"""米游社用户页面。"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from ...core import Storage
from ..models import GenericTableModel
from .base import BasePage


class UserPostsPage(BasePage):
    """抓取米游社用户发帖并提取发帖时间。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table_model = GenericTableModel(
            ["序号", "发帖ID", "标题", "时间", "链接"],
            self._load,
            [
                lambda item: item.post_id,
                lambda item: item.title,
                lambda item: item.created_at,
                lambda item: item.url,
            ],
            numbered=True,
            parent=self,
        )
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(self.make_header("米游社用户", "抓取用户发帖页面 HTML，并提取发帖时间"))

        self.btn_fetch = self.make_button("全量抓取", lambda: self._fetch(incremental=False))
        self.btn_incremental = self.make_button("增量抓取", lambda: self._fetch(incremental=True))
        self.btn_extract = self.make_button("提取时间", lambda: self._extract(incremental=False))
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
                4: QHeaderView.ResizeMode.Interactive,
            },
        )
        layout.addWidget(self.table, 1)

        self.reload_table()

    # ------------------------------------------------------------------ #
    #  动作
    # ------------------------------------------------------------------ #
    def _fetch(self, *, incremental: bool) -> None:
        from ...scrapers import run_user

        mode = "增量" if incremental else "全量"
        self.run_task(lambda: run_user(incremental=incremental), f"{mode}抓取用户发帖")

    def _extract(self, *, incremental: bool) -> None:
        from ...extractors import run_extract_posts

        mode = "增量" if incremental else "全量"
        self.run_task(lambda: run_extract_posts(incremental=incremental), f"{mode}提取用户发帖")

    # ------------------------------------------------------------------ #
    #  数据
    # ------------------------------------------------------------------ #
    @staticmethod
    def _load() -> list[object]:
        with Storage() as store:
            return list(store.query_posts())


__all__ = ["UserPostsPage"]
