"""Controller 层：把 View 的请求转成后台任务，并把结果回传 View。

* :class:`TaskController` —— 通用任务控制器：在 ``QThread`` 中执行 core 服务，
  转发进度 / 日志 / 结果 / 失败 / 取消信号，供页面绑定 Model 刷新。
* :class:`SystemController` —— 系统工具页的 core 服务门面（备份、配置、系统信息、
  数据迁移、缓存清理），本身不做线程调度。
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal

from ..core import Storage, get_path_manager, reload_settings
from ..core.exceptions import ConfigError
from ..utils import BackupInfo, backup_manager, check_and_migrate
from .workers import TaskWorker

#: 后台任务的可调用对象
TaskFunc = Callable[..., object]

#: 数据库备份对应的源文件名
_DB_FILENAME = "toolkit.db"


class TaskController(QObject):
    """后台任务控制器（一个实例同时只跑一个任务）。

    Signals:
        started: 任务已启动。
        progress: 百分比进度（0-100）。
        message: 一行日志输出。
        finished: 任务成功结束，携带返回值。
        failed: 任务异常结束，携带错误描述。
        cancelled: 任务被用户中断。
    """

    started = Signal()
    progress = Signal(int)
    message = Signal(str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: TaskWorker | None = None

    # ------------------------------------------------------------------ #
    #  状态
    # ------------------------------------------------------------------ #
    @property
    def is_running(self) -> bool:
        """是否有任务正在运行。"""
        return self._worker is not None

    # ------------------------------------------------------------------ #
    #  控制
    # ------------------------------------------------------------------ #
    def run(self, func: TaskFunc, *args: Any, label: str = "任务", **kwargs: Any) -> bool:
        """在后台线程启动任务；已有任务在跑时返回 False。"""
        if self._worker is not None:
            return False

        worker = TaskWorker(func, *args, label=label, **kwargs)
        self._worker = worker

        worker.progress.connect(self.progress)
        worker.message.connect(self.message)
        worker.finished_ok.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._on_thread_finished)
        worker.finished.connect(worker.deleteLater)

        self.message.emit(f"[START] {label}")
        self.started.emit()
        worker.start()
        return True

    def stop(self) -> None:
        """请求中断当前任务（协作式）。"""
        if self._worker is not None:
            self._worker.request_cancellation()

    def report_progress(self, percent: int) -> None:
        """供任务函数在后台线程上报百分比进度。"""
        self.progress.emit(max(0, min(100, int(percent))))

    def report_message(self, text: str) -> None:
        """供任务函数在后台线程输出日志。"""
        self.message.emit(text)

    # ------------------------------------------------------------------ #
    #  Worker 回调
    # ------------------------------------------------------------------ #
    def _on_finished(self, result: object) -> None:
        self.message.emit("[OK] 任务完成")
        self.finished.emit(result)

    def _on_failed(self, message: str) -> None:
        self.message.emit(f"[ERROR] {message}")
        self.failed.emit(message)

    def _on_cancelled(self) -> None:
        self.cancelled.emit()

    def _on_thread_finished(self) -> None:
        self._worker = None


class SystemController(QObject):
    """系统工具页涉及的 core 服务（备份 / 配置 / 信息 / 迁移 / 清理）。"""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    # ------------------------------------------------------------------ #
    #  备份
    # ------------------------------------------------------------------ #
    def list_backups(self) -> list[BackupInfo]:
        """列出全部备份（按创建时间倒序）。"""
        base = backup_manager.backup_dir
        infos: list[BackupInfo] = []
        for sub in sorted(path for path in base.iterdir() if path.is_dir()):
            infos.extend(backup_manager.list_backups(sub.name))
        infos.sort(key=lambda info: info.created_at, reverse=True)
        return infos

    def latest_database_backup(self) -> BackupInfo | None:
        """返回最新的数据库备份。"""
        infos = backup_manager.list_backups(_DB_FILENAME)
        return infos[0] if infos else None

    def restore_database_backup(self, info: BackupInfo) -> bool:
        """用备份覆盖当前数据库文件。"""
        return backup_manager.restore_backup(info.filepath, get_path_manager().db)

    # ------------------------------------------------------------------ #
    #  配置
    # ------------------------------------------------------------------ #
    def read_config_text(self) -> str:
        """读取 ``config.toml`` 原文；文件不存在时返回空串。"""
        path = get_path_manager().config_file
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def write_config_text(self, text: str) -> None:
        """写入 ``config.toml`` 并重新加载配置。"""
        path = get_path_manager().config_file
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"写入配置文件失败: {path}", detail=str(exc)) from exc
        reload_settings()

    def reload_config(self) -> object:
        """重新加载配置（供后台任务调用）。"""
        return reload_settings()

    # ------------------------------------------------------------------ #
    #  系统信息
    # ------------------------------------------------------------------ #
    def system_info(self) -> list[str]:
        """收集系统 / 运行环境信息（缺失的可选依赖降级提示）。"""
        paths = get_path_manager()
        lines = [
            f"[INFO] 操作系统：{platform.system()} {platform.release()}",
            f"[INFO] Python：{sys.version.split()[0]}",
            f"[INFO] 项目根目录：{paths.root}",
            f"[INFO] 数据目录：{paths.relative(paths.data)}",
            f"[INFO] 数据库：{paths.relative(paths.db)}",
        ]
        try:
            import PySide6

            lines.append(f"[INFO] PySide6：{PySide6.__version__}")
        except ImportError:
            lines.append("[WARN] PySide6：未安装")
        try:
            from playwright._repo_version import version as pw_version

            lines.append(f"[INFO] Playwright：{pw_version}")
        except ImportError:
            lines.append("[WARN] Playwright：未安装")
        lines.extend(
            [
                "",
                "--- 字体来源 ---",
                "游戏字体来自 HoYo-Glyphs 项目：",
                "  https://github.com/SpeedyOrc-C/HoYo-Glyphs",
                "仅供非商业用途使用，字体文件未做修改。",
            ]
        )
        return lines

    # ------------------------------------------------------------------ #
    #  迁移 / 清理
    # ------------------------------------------------------------------ #
    def migrate(self) -> None:
        """执行旧数据迁移（幂等，异常仅记录日志）。"""
        check_and_migrate()

    def cleanup(self) -> list[str]:
        """清理多余备份并压缩数据库，返回日志行。"""
        removed = backup_manager.prune(backup_manager.max_backups)
        lines = [f"[OK] 已清理旧备份 {removed} 份"]
        with Storage() as store:
            store.vacuum()
        lines.append("[OK] 数据库已压缩")
        return lines


__all__ = ["SystemController", "TaskController", "TaskFunc"]
