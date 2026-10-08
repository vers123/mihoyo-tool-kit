"""GUI 冒烟测试（offscreen 平台）。

覆盖 v2 声明的 GUI 关键路径，作为 ``gui/`` 的回归护栏：

* 导航由 CLI 命令注册表派生，43 条命令恰好各有一个页面入口；
* 主窗口可构建，标题带版本号，导航项与页面一一对应；
* 主题调色板与样式表可用，系统深浅色探测不抛异常；
* ``TaskController`` 能把任务放到后台线程执行并回传结果；
* 协作式取消可中断长任务。

CI 环境没有显示设备，统一使用 Qt ``offscreen`` 平台插件；若运行环境缺少 Qt 依赖
（例如 ubuntu 未装 ``libegl1``，``import PySide6`` 会抛 ImportError），整个模块跳过
而不是失败 —— 注意 pytest 8.2 起 ``importorskip`` 不再吞掉这类 ImportError，故这里
显式捕获。
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable

import pytest

# offscreen 必须在导入 PySide6 / 创建 QApplication 之前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - 取决于运行环境
    pytest.skip(f"PySide6 不可用：{exc}", allow_module_level=True)

from mihoyo_toolkit import __version__
from mihoyo_toolkit.cli.registry import CommandRegistry, registry
from mihoyo_toolkit.core.exceptions import GuiError
from mihoyo_toolkit.gui import MainWindow, theme
from mihoyo_toolkit.gui.controllers import TaskController
from mihoyo_toolkit.gui.nav import build_nav

#: 等待后台线程信号的最长秒数
TIMEOUT_SECONDS = 20.0


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    """创建（或复用）QApplication；平台插件不可用时跳过整个模块。"""
    try:
        app = QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - 取决于运行环境
        pytest.skip(f"Qt 平台不可用：{exc}")
    return app  # type: ignore[no-any-return]


def _spin_until(qt_app: QApplication, predicate: Callable[[], bool]) -> bool:
    """自旋事件循环直到条件成立或超时。"""
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        qt_app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    qt_app.processEvents()
    return predicate()


# ---------------------------------------------------------------------- #
#  导航：由命令注册表派生（无需 Qt 平台）
# ---------------------------------------------------------------------- #
def test_nav_entries_cover_registry_exactly() -> None:
    """每条注册命令恰好被一个页面负责，标题与顺序取自注册表。"""
    entries = build_nav()
    covered = [key for entry in entries for key in entry.commands]
    expected = [cmd.key for cmd in registry.all()]

    assert sorted(covered) == sorted(expected)
    assert len(covered) == len(set(covered))

    groups = list(registry.by_group())
    assert entries[0].title == groups[0]
    assert "TXT 过滤" in [entry.title for entry in entries]


def test_build_nav_rejects_unmapped_group() -> None:
    """注册表出现未登记的分组时抛出 GuiError，而不是静默少一个入口。"""
    reg = CommandRegistry()
    reg.register(key="unknown.thing", label="未知命令", description="", group="未知分组")(
        lambda: None
    )

    with pytest.raises(GuiError):
        build_nav(reg)


# ---------------------------------------------------------------------- #
#  Qt 相关
# ---------------------------------------------------------------------- #
def test_main_window_builds_and_matches_nav(qt_app: QApplication) -> None:
    """主窗口可构建，导航项与页面栈一一对应，切换导航会切页。"""
    window = MainWindow()
    try:
        assert __version__ in window.windowTitle()
        assert window.nav_list.count() == len(window.nav_entries)
        assert window.content_stack.count() == window.nav_list.count()
        assert window.content_stack.currentIndex() == 0

        window.nav_list.setCurrentRow(3)
        assert window.content_stack.currentIndex() == 3
        assert window.statusBar().currentMessage() == f"当前：{window.nav_entries[3].title}"
    finally:
        window.close()


def test_theme_palettes_and_stylesheet(qt_app: QApplication) -> None:
    """浅色 / 深色调色板与样式表可用，系统主题探测返回布尔值。"""
    assert theme.LIGHT is not theme.DARK
    assert theme.app_stylesheet()
    assert isinstance(theme.detect_system_dark(), bool)

    theme.apply_to_application(qt_app)
    window = MainWindow()
    try:
        window.apply_theme()
    finally:
        window.close()


def test_worker_runs_task_in_background(qt_app: QApplication) -> None:
    """TaskController 在后台线程执行任务并回传返回值。"""
    controller = TaskController()
    results: list[object] = []
    controller.finished.connect(results.append)

    assert controller.run(lambda: 41 + 1, label="冒烟") is True
    assert _spin_until(qt_app, lambda: not controller.is_running)
    assert results == [42]


def test_worker_cooperative_cancellation(qt_app: QApplication) -> None:
    """协作式取消：请求中断后长任务以 cancelled 信号结束。"""
    controller = TaskController()
    cancelled: list[bool] = []
    controller.cancelled.connect(lambda: cancelled.append(True))

    def _long_task() -> None:
        for _ in range(2000):
            print("tick")
            time.sleep(0.005)

    assert controller.run(_long_task, label="可取消") is True
    controller.stop()

    assert _spin_until(qt_app, lambda: bool(cancelled))
    assert _spin_until(qt_app, lambda: not controller.is_running)
