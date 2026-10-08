"""系统工具页面 + 数据导出页面。

``SystemPage`` 负责备份管理、配置查看 / 编辑、系统信息、数据迁移与缓存清理；
``ExportPage`` 负责把新闻导出为 Excel / RSS / JSON Feed。

两个页面的 core 调用都集中在 :class:`SystemController` / exporters 中，
页面本身只构建控件与展示结果。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core import get_path_manager
from ..controllers import SystemController
from .base import BasePage


class SystemPage(BasePage):
    """系统工具：备份 / 配置 / 信息 / 迁移 / 清理。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.system = SystemController(self)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(
            self.make_header("系统工具", "备份管理、配置编辑、系统信息、数据迁移与缓存清理")
        )

        self.btn_list_backup = self.make_button("查看备份", self._list_backups)
        self.btn_restore = self.make_button("恢复备份", self._restore_backup)
        self.btn_view_config = self.make_button("查看配置", self._view_config)
        self.btn_edit_config = self.make_button("修改配置", self._edit_config)
        self.btn_reload_config = self.make_button("重载配置", self._reload_config)

        first_row = QHBoxLayout()
        first_row.setSpacing(8)
        for button in (
            self.btn_list_backup,
            self.btn_restore,
            self.btn_view_config,
            self.btn_edit_config,
            self.btn_reload_config,
        ):
            first_row.addWidget(button)
        first_row.addStretch()
        layout.addLayout(first_row)

        self.btn_info = self.make_button("系统信息", self._show_system_info)
        self.btn_migrate = self.make_button("数据迁移", self._run_migration)
        self.btn_cleanup = self.make_button("清理缓存", self._cleanup)

        second_row = QHBoxLayout()
        second_row.setSpacing(8)
        for button in (self.btn_info, self.btn_migrate, self.btn_cleanup):
            second_row.addWidget(button)
        second_row.addStretch()
        layout.addLayout(second_row)

        layout.addLayout(self.make_stop_row())
        layout.addWidget(self.progress)

        self.config_editor = QPlainTextEdit()
        self.config_editor.setVisible(False)
        self.config_editor.setMaximumHeight(260)
        layout.addWidget(self.config_editor)

        self.btn_save_config = self.make_button("保存配置", self._save_config)
        self.btn_save_config.setVisible(False)
        save_row = QHBoxLayout()
        save_row.addStretch()
        save_row.addWidget(self.btn_save_config)
        layout.addLayout(save_row)

        layout.addStretch()

        self.register_buttons(
            self.btn_list_backup,
            self.btn_restore,
            self.btn_view_config,
            self.btn_edit_config,
            self.btn_reload_config,
            self.btn_info,
            self.btn_migrate,
            self.btn_cleanup,
            self.btn_save_config,
        )

    # ------------------------------------------------------------------ #
    #  备份
    # ------------------------------------------------------------------ #
    def _list_backups(self) -> None:
        infos = self.system.list_backups()
        if not infos:
            self.log_message.emit("[INFO] 暂无备份")
            return
        self.log_message.emit(f"[INFO] 共 {len(infos)} 份备份（按时间倒序）：")
        for info in infos:
            size_kb = info.size / 1024
            self.log_message.emit(
                f"  {info.created_at:%Y-%m-%d %H:%M:%S}  {info.filepath.name}  {size_kb:.1f} KB"
            )

    def _restore_backup(self) -> None:
        info = self.system.latest_database_backup()
        if info is None:
            self.log_message.emit("[INFO] 没有可恢复的数据库备份")
            return

        answer = QMessageBox.question(
            self,
            "确认恢复",
            f"将使用备份「{info.filepath.name}」覆盖当前数据库，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.run_task(lambda: self.system.restore_database_backup(info), "恢复数据库备份")

    # ------------------------------------------------------------------ #
    #  配置
    # ------------------------------------------------------------------ #
    def _view_config(self) -> None:
        self._load_config_editor(editable=False)

    def _edit_config(self) -> None:
        self._load_config_editor(editable=True)

    def _load_config_editor(self, *, editable: bool) -> None:
        try:
            text = self.system.read_config_text()
        except OSError as exc:
            QMessageBox.critical(self, "读取失败", str(exc))
            return
        if not text:
            self.log_message.emit("[WARN] 配置文件不存在或为空")
            return
        self.config_editor.setPlainText(text)
        self.config_editor.setReadOnly(not editable)
        self.config_editor.setVisible(True)
        self.btn_save_config.setVisible(editable)

    def _save_config(self) -> None:
        text = self.config_editor.toPlainText()
        try:
            self.system.write_config_text(text)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.config_editor.setReadOnly(True)
        self.btn_save_config.setVisible(False)
        self.log_message.emit("[OK] 配置已保存并重新加载")

    def _reload_config(self) -> None:
        self.run_task(self.system.reload_config, "重新加载配置")

    # ------------------------------------------------------------------ #
    #  信息 / 迁移 / 清理
    # ------------------------------------------------------------------ #
    def _show_system_info(self) -> None:
        for line in self.system.system_info():
            self.log_message.emit(line)

    def _run_migration(self) -> None:
        self.run_task(self.system.migrate, "数据迁移")

    def _cleanup(self) -> None:
        answer = QMessageBox.question(
            self,
            "确认清理",
            "将清理多余的历史备份并压缩数据库，此操作不可撤销，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.run_task(self.system.cleanup, "清理缓存")

    # ------------------------------------------------------------------ #
    #  任务回调
    # ------------------------------------------------------------------ #
    def _on_task_finished(self, result: object) -> None:
        self._restore_controls()
        self.progress.finish("任务完成")
        if isinstance(result, list):
            for line in result:
                self.log_message.emit(str(line))


class ExportPage(BasePage):
    """数据导出：Excel / RSS / JSON Feed。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  界面
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        output_dir = get_path_manager().relative(get_path_manager().output)
        layout.addWidget(self.make_header("数据导出", f"把数据库中的新闻导出到 {output_dir}"))

        self.btn_excel = self.make_button("导出 Excel", self._export_excel)
        self.btn_rss = self.make_button("导出 RSS", self._export_rss)
        self.btn_json = self.make_button("导出 JSON Feed", self._export_json)
        self.register_buttons(self.btn_excel, self.btn_rss, self.btn_json)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        for button in (self.btn_excel, self.btn_rss, self.btn_json):
            button_row.addWidget(button)
        button_row.addStretch()
        button_row.addWidget(self.btn_stop)
        layout.addLayout(button_row)

        layout.addWidget(self.progress)
        layout.addStretch()

    # ------------------------------------------------------------------ #
    #  动作
    # ------------------------------------------------------------------ #
    def _export_excel(self) -> None:
        from ...exporters import export_news_excel

        self.run_task(export_news_excel, "导出 Excel")

    def _export_rss(self) -> None:
        from ...exporters import generate_rss_feed

        self.run_task(generate_rss_feed, "导出 RSS")

    def _export_json(self) -> None:
        from ...exporters import generate_json_feed

        self.run_task(generate_json_feed, "导出 JSON Feed")

    # ------------------------------------------------------------------ #
    #  任务回调
    # ------------------------------------------------------------------ #
    def _on_task_finished(self, result: object) -> None:
        self._restore_controls()
        if isinstance(result, Path):
            relative = get_path_manager().relative(result)
            self.progress.finish(f"已导出：{relative}")
            self.log_message.emit(f"[OK] 导出完成：{relative}")
        else:
            self.progress.finish("任务完成")


__all__ = ["ExportPage", "SystemPage"]
