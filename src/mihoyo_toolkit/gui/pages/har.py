"""HAR 文件管理页面。

展示各抓取器 HAR 目录的当前生效文件，并提供「更新 HAR」（清理旧文件）与
「打开 HAR 目录」入口，便于用户随时放入新导出的 HAR 后立即生效。
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QVBoxLayout, QWidget

from ...core import get_path_manager, get_settings
from ...utils import HarUpdateReport, har_site_status, update_har_files
from ..models import GenericTableModel
from .base import BasePage

#: 表格列宽策略
_COLUMN_MODES: dict[int, QHeaderView.ResizeMode] = {
    0: QHeaderView.ResizeMode.ResizeToContents,  # 序号
    1: QHeaderView.ResizeMode.ResizeToContents,  # 站点
    2: QHeaderView.ResizeMode.ResizeToContents,  # 目录
    3: QHeaderView.ResizeMode.Stretch,  # 当前 HAR
    4: QHeaderView.ResizeMode.ResizeToContents,  # 保存时间
    5: QHeaderView.ResizeMode.ResizeToContents,  # 大小
    6: QHeaderView.ResizeMode.ResizeToContents,  # 类型
    7: QHeaderView.ResizeMode.ResizeToContents,  # 文件数
}


class HarPage(BasePage):
    """HAR 目录检查 / 清理。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table_model = GenericTableModel(
            ["站点", "目录", "当前 HAR", "保存时间", "大小", "类型", "文件数"],
            har_site_status,
            [
                lambda item: item.name,
                lambda item: get_path_manager().relative(item.directory),
                lambda item: item.current.name if item.current else "（缺失）",
                lambda item: item.current.saved_at_text if item.current else "",
                lambda item: item.current.size_text if item.current else "",
                lambda item: item.current.kind if item.current else "",
                lambda item: len(item.files),
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

        paths = get_path_manager()
        layout.addWidget(
            self.make_header(
                "HAR 文件管理",
                f"HAR 用于接口失效时回退解析；{paths.relative(paths.har)}/ 下每个目录只保留"
                "最新的文件。把新导出的 HAR 放入对应目录后，点击「更新 HAR」即可生效",
            )
        )

        self.btn_refresh = self.make_button("刷新列表", self.refresh_har)
        self.btn_update = self.make_button("更新 HAR", self._update_har)
        self.btn_open = self.make_button("打开 HAR 目录", self._open_har_dir)
        self.register_buttons(self.btn_refresh, self.btn_update)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        for button in (self.btn_refresh, self.btn_update, self.btn_open):
            button_row.addWidget(button)
        button_row.addStretch()
        button_row.addWidget(self.btn_stop)
        layout.addLayout(button_row)

        layout.addWidget(self.progress)

        self.table = self.make_table(self.table_model)
        self.set_column_modes(self.table, _COLUMN_MODES)
        layout.addWidget(self.table, 1)

        self.reload_table()

    # ------------------------------------------------------------------ #
    #  动作
    # ------------------------------------------------------------------ #
    def refresh_har(self) -> None:
        """重新扫描 har 目录并刷新表格。"""
        self.reload_table()

    def _update_har(self) -> None:
        self.run_task(
            lambda: update_har_files(keep=get_settings().har.keep_files),
            "更新 HAR",
        )

    def _open_har_dir(self) -> None:
        directory = get_path_manager().har
        directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    # ------------------------------------------------------------------ #
    #  任务回调
    # ------------------------------------------------------------------ #
    def _on_task_finished(self, result: object) -> None:
        self._restore_controls()
        if not isinstance(result, HarUpdateReport):
            self.progress.finish("任务完成")
            self.reload_table()
            return

        paths = get_path_manager()
        if result.removed:
            self.progress.finish(f"已清理 {len(result.removed)} 个旧 HAR")
            for path in result.removed:
                self.log_message.emit(f"[OK] 已删除 {paths.relative(path)}")
        else:
            self.progress.finish("无需清理旧 HAR")
        self.log_message.emit(f"[INFO] 当前保留 {len(result.kept)} 个 HAR 文件")
        self.reload_table()


__all__ = ["HarPage"]
