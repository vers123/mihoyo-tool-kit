"""GUI 截图脚本（offscreen 渲染，用于视觉回归对比）。

用法::

    python scripts/render_gui_screenshots.py --out docs/screenshots/before
    python scripts/render_gui_screenshots.py --out docs/screenshots/after

生成：

* ``gui-home-light.png`` / ``gui-home-dark.png`` —— 首页（浅色 / 深色）
* ``gui-news-light.png`` —— 新闻页（浅色）

脚本只依赖 PySide6 的 offscreen 平台，不弹窗、不联网。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

#: 必须在导入 PySide6 之前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

WINDOW_SIZE = (1180, 780)


def _capture(window, path: Path) -> Path:
    """渲染窗口并保存为 PNG。"""
    from PySide6.QtWidgets import QApplication

    window.resize(*WINDOW_SIZE)
    window.show()
    # 让布局、样式表与「延迟重排」的定时器都完成一次
    for _ in range(4):
        QApplication.processEvents()
        window.repaint()
    pixmap = window.grab()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(path), "PNG"):
        raise SystemExit(f"截图保存失败: {path}")
    return path


def _select(window, row: int) -> None:
    """切换到指定页（兼容有无首页的新旧布局）。"""
    select_page = getattr(window, "select_page", None)
    if callable(select_page):
        select_page(row)
    else:  # pragma: no cover - 旧布局兜底
        window.nav_list.setCurrentRow(row)


def main(argv: list[str] | None = None) -> int:
    """脚本入口。"""
    parser = argparse.ArgumentParser(description="渲染 GUI 截图（offscreen）")
    parser.add_argument("--out", default="docs/screenshots/after", help="输出目录")
    args = parser.parse_args(argv)

    out_dir = Path(args.out).resolve()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # pragma: no cover - 环境相关
        raise SystemExit(f"PySide6 不可用: {exc}") from exc

    from mihoyo_toolkit.gui import MainWindow, theme
    from mihoyo_toolkit.gui.fonts import apply_app_font, load_game_fonts, load_main_font

    app = QApplication.instance() or QApplication([])
    # 与 launch_gui() 一致：先注册思源黑体与游戏字体，否则 offscreen 下中文会显示为方块
    apply_app_font(app, load_main_font())
    fonts = load_game_fonts()
    generated: list[Path] = []

    for mode, suffix in (("light", "light"), ("dark", "dark")):
        theme.apply_to_application(app, theme.LIGHT if mode == "light" else theme.DARK)
        window = MainWindow(fonts=fonts)
        try:
            _select(window, 0)
            window.show()
            generated.append(_capture(window, out_dir / f"gui-home-{suffix}.png"))
            if mode == "light":
                _select(window, 1)
                generated.append(_capture(window, out_dir / "gui-news-light.png"))
        finally:
            window.close()

    for path in generated:
        print(f"[OK] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
