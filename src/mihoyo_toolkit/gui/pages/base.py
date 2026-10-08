"""页面基类：统一任务调度、进度条、停止按钮与结果表格刷新。

View 层只构建控件与展示数据；所有耗时操作通过 :class:`TaskController`
交给后台线程，页面通过信号把输出写入全局日志面板。

子类约定：``__init__`` 内先 ``super().__init__()``，再设置自身属性，
最后调用 ``self._setup_ui()``（基类不自动调用，以便子类先完成参数注入）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QAbstractItemModel, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..controllers import TaskController, TaskFunc
from ..models import GenericTableModel
from ..widgets import ProgressWidget


class BasePage(QWidget):
    """功能页面基类。

    Signals:
        log_message: 需要写入全局日志面板的一行文本。
    """

    log_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = TaskController(self)
        self.progress = ProgressWidget(self)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setVisible(False)
        self.btn_stop.clicked.connect(self.stop_task)
        #: 结果表格模型（无表格的页面保持 None，任务结束后自动刷新）
        self.table_model: GenericTableModel | None = None
        self._action_buttons: list[QPushButton] = []
        self._connect_controller()

    # ------------------------------------------------------------------ #
    #  子类扩展点
    # ------------------------------------------------------------------ #
    def _setup_ui(self) -> None:
        """子类实现：构建页面控件。"""

    # ------------------------------------------------------------------ #
    #  初始化
    # ------------------------------------------------------------------ #
    def _connect_controller(self) -> None:
        """把控制器信号接到页面槽函数。"""
        self.controller.message.connect(self.log_message.emit)
        self.controller.progress.connect(self.progress.set_percent)
        self.controller.finished.connect(self._on_task_finished)
        self.controller.failed.connect(self._on_task_failed)
        self.controller.cancelled.connect(self._on_task_cancelled)

    # ------------------------------------------------------------------ #
    #  控件工厂
    # ------------------------------------------------------------------ #
    def make_header(self, title: str, subtitle: str = "") -> QWidget:
        """构建页面标题区（标题 + 灰字说明）。"""
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title_label = QLabel(title)
        font = title_label.font()
        font.setPointSizeF(font.pointSizeF() + theme.TITLE_OFFSET)
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            # 颜色交由全局样式表控制（objectName 选择器），以便主题切换时自动更新
            subtitle_label.setObjectName("pageSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        return box

    def make_button(self, text: str, handler: Callable[..., Any]) -> QPushButton:
        """创建按钮并绑定点击处理。"""
        button = QPushButton(text)
        button.clicked.connect(handler)
        return button

    def make_stop_row(self) -> QHBoxLayout:
        """创建「停止」按钮行（右对齐）。"""
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.btn_stop)
        return row

    def register_buttons(self, *buttons: QPushButton) -> None:
        """登记需要在任务执行期间禁用的按钮。"""
        self._action_buttons.extend(buttons)

    def make_table(self, model: QAbstractItemModel | None) -> QTableView:
        """创建只读结果表格。"""
        view = QTableView()
        view.setModel(model)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setAlternatingRowColors(True)
        view.setWordWrap(False)
        view.verticalHeader().setVisible(False)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        view.setMinimumHeight(180)
        return view

    @staticmethod
    def set_column_modes(view: QTableView, modes: dict[int, QHeaderView.ResizeMode]) -> None:
        """按列设置宽度策略。"""
        header = view.horizontalHeader()
        for column, mode in modes.items():
            header.setSectionResizeMode(column, mode)

    # ------------------------------------------------------------------ #
    #  任务调度
    # ------------------------------------------------------------------ #
    def run_task(self, func: TaskFunc, label: str, *args: object, **kwargs: object) -> bool:
        """在后台线程执行任务并切换到忙碌状态。"""
        if self.controller.is_running:
            self.log_message.emit("[WARN] 已有任务正在运行，请等待完成")
            return False

        self.progress.start(label)
        self.btn_stop.setVisible(True)
        self.btn_stop.setEnabled(True)
        self._set_buttons_enabled(False)

        if not self.controller.run(func, *args, label=label, **kwargs):
            self._restore_controls()
            return False
        return True

    def stop_task(self) -> None:
        """请求中断当前任务。"""
        if not self.controller.is_running:
            return
        self.log_message.emit("[INFO] 正在请求中断任务…")
        self.controller.stop()
        self.btn_stop.setEnabled(False)

    # ------------------------------------------------------------------ #
    #  任务回调
    # ------------------------------------------------------------------ #
    def _on_task_finished(self, result: object) -> None:
        self.progress.finish("任务完成")
        self._restore_controls()
        self.reload_table()

    def _on_task_failed(self, message: str) -> None:
        self.progress.reset(f"失败：{message}")
        self._restore_controls()

    def _on_task_cancelled(self) -> None:
        self.progress.reset("已中断")
        self._restore_controls()

    def reload_table(self) -> None:
        """重新装载结果表格（无表格时跳过）。"""
        model = self.table_model
        if model is None:
            return
        count = model.reload()
        if model.last_error:
            self.log_message.emit(f"[WARN] 加载表格数据失败：{model.last_error}")
            return
        self.log_message.emit(f"[INFO] 当前表格共 {count} 条记录")

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #
    def _set_buttons_enabled(self, enabled: bool) -> None:
        for button in self._action_buttons:
            button.setEnabled(enabled)

    def _restore_controls(self) -> None:
        self._set_buttons_enabled(True)
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(True)


__all__ = ["BasePage"]
