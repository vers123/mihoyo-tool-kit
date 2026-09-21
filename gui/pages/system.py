"""系统工具页面"""

import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit
)
from gui.workers import ScraperWorker
from gui.widgets import ProgressWidget
from core.config_manager import config_manager


class SystemPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(self._make_label("系统工具"))
        layout.addWidget(self._make_label("备份管理、配置编辑、系统信息、数据迁移"))

        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        self.btn_list_backup = QPushButton("查看备份")
        self.btn_list_backup.clicked.connect(self._list_backups)

        self.btn_restore = QPushButton("恢复备份")
        self.btn_restore.clicked.connect(self._restore_backup)

        self.btn_config = QPushButton("查看配置")
        self.btn_config.clicked.connect(self._show_config)

        self.btn_reload = QPushButton("重载配置")
        self.btn_reload.clicked.connect(self._reload_config)

        for btn in (self.btn_list_backup, self.btn_restore, self.btn_config, self.btn_reload):
            btn_row1.addWidget(btn)
        btn_row1.addStretch()
        layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        self.btn_edit_config = QPushButton("修改配置")
        self.btn_edit_config.clicked.connect(self._edit_config)

        self.btn_info = QPushButton("系统信息")
        self.btn_info.clicked.connect(self._show_system_info)

        self.btn_migrate = QPushButton("数据迁移")
        self.btn_migrate.clicked.connect(self._run_migration)

        for btn in (self.btn_edit_config, self.btn_info, self.btn_migrate):
            btn_row2.addWidget(btn)
        btn_row2.addStretch()
        layout.addLayout(btn_row2)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self._stop_task)
        stop_layout = QHBoxLayout()
        stop_layout.addStretch()
        stop_layout.addWidget(self.btn_stop)
        layout.addLayout(stop_layout)

        self.progress = ProgressWidget()
        layout.addWidget(self.progress)

        self.config_editor = QPlainTextEdit()
        self.config_editor.setVisible(False)
        self.config_editor.setMaximumHeight(250)
        layout.addWidget(self.config_editor)

        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.btn_save_config = QPushButton("保存配置")
        self.btn_save_config.setVisible(False)
        self.btn_save_config.clicked.connect(self._save_config)
        save_layout.addWidget(self.btn_save_config)
        layout.addLayout(save_layout)

        layout.addStretch()

    def _make_label(self, text):
        lbl = QLabel(text)
        return lbl

    def _list_backups(self):
        import os
        from utils.backup_manager import backup_manager
        backup_dir = backup_manager.backup_dir
        msg_lines = ["备份列表："]
        if os.path.exists(backup_dir):
            for sub in sorted(os.listdir(backup_dir)):
                sub_path = os.path.join(backup_dir, sub)
                if os.path.isdir(sub_path):
                    files = os.listdir(sub_path)
                    if files:
                        msg_lines.append(f"  [{sub}] {len(files)} 个备份:")
                        for f in sorted(files, reverse=True):
                            msg_lines.append(f"    {f}")
        if len(msg_lines) == 1:
            msg_lines.append("  (无备份)")
        main_window = self.window()
        if hasattr(main_window, 'log_viewer'):
            for line in msg_lines:
                main_window.log_viewer.append_log(line)

    def _restore_backup(self):
        import os
        from utils.backup_manager import backup_manager
        backup_dir = backup_manager.backup_dir
        latest_backup = None
        latest_subdir = None
        if os.path.exists(backup_dir):
            for sub in os.listdir(backup_dir):
                sub_path = os.path.join(backup_dir, sub)
                if os.path.isdir(sub_path):
                    latest = backup_manager.get_latest_backup(f"{sub}.html")
                    if latest:
                        latest_backup = latest
                        latest_subdir = sub
                        break

        if not latest_backup:
            main_window = self.window()
            if hasattr(main_window, 'log_viewer'):
                main_window.log_viewer.append_log("[INFO] 没有可恢复的备份")
            return

        target_path = os.path.join("data", "html", latest_subdir, f"{latest_subdir}.html")

        def _restore():
            backup_manager.restore_backup(latest_backup, target_path)
        self._run_worker(_restore, "恢复备份中...")

    def _show_config(self):
        config_path = os.path.join(config_manager.get_project_root(), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            formatted = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
            self.config_editor.setPlainText(formatted)
            self.config_editor.setVisible(True)
            self.btn_save_config.setVisible(True)

    def _edit_config(self):
        self._show_config()
        self.config_editor.setReadOnly(False)

    def _save_config(self):
        config_path = os.path.join(config_manager.get_project_root(), "config.json")
        try:
            data = json.loads(self.config_editor.toPlainText())
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            config_manager.load_config()
            self.config_editor.setReadOnly(True)
            main_window = self.window()
            if hasattr(main_window, 'log_viewer'):
                main_window.log_viewer.append_log("[OK] 配置保存成功")
        except json.JSONDecodeError as e:
            main_window = self.window()
            if hasattr(main_window, 'log_viewer'):
                main_window.log_viewer.append_log(f"[ERROR] JSON 格式错误: {e}")

    def _reload_config(self):
        def _reload():
            config_manager.load_config()
            print("[OK] 配置已重新加载")
        self._run_worker(_reload, "重新加载配置中...")

    def _show_system_info(self):
        import platform
        import sys
        lines = [
            f"[INFO] 操作系统: {platform.system()} {platform.version()}",
            f"[INFO] Python: {sys.version.split()[0]}",
            f"[INFO] 工作目录: {config_manager.get_project_root()}",
        ]
        try:
            import playwright
            lines.append(f"[INFO] Playwright: 已安装")
        except ImportError:
            lines.append(f"[WARN] Playwright: 未安装")
        try:
            import PySide6
            lines.append(f"[INFO] PySide6: {PySide6.__version__}")
        except ImportError:
            lines.append(f"[WARN] PySide6: 未安装")
        lines.append("")
        lines.append("--- 字体来源 ---")
        lines.append("游戏字体来自 HoYo-Glyphs 项目:")
        lines.append("  https://github.com/SpeedyOrc-C/HoYo-Glyphs")
        lines.append("仅供非商业用途使用，字体文件未做修改。")
        lines.append("完整许可详见 resources/font/LICENSE")
        main_window = self.window()
        if hasattr(main_window, 'log_viewer'):
            for line in lines:
                main_window.log_viewer.append_log(line)

    def _run_migration(self):
        from utils.migration import check_and_migrate
        self._run_worker(check_and_migrate, "数据迁移中...")

    def _run_worker(self, func, text):
        if self.worker and self.worker.isRunning():
            return
        self.progress.start(text=text)
        self._set_buttons_enabled(False)
        self.btn_stop.setVisible(True)
        self.worker = ScraperWorker(func)
        main_window = self.window()
        if hasattr(main_window, 'log_viewer'):
            self.worker.log_message.connect(main_window.log_viewer.append_log)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.start()

    def _stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_interruption()
            self.btn_stop.setEnabled(False)

    def _on_finished(self, success, message):
        self.progress.finish(message if success else f"失败: {message}")
        self._set_buttons_enabled(True)
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(True)
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _set_buttons_enabled(self, enabled):
        for btn in (self.btn_list_backup, self.btn_restore, self.btn_config,
                     self.btn_reload, self.btn_edit_config, self.btn_info, self.btn_migrate):
            btn.setEnabled(enabled)
