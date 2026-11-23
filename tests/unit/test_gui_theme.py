"""GUI 主题与界面状态测试。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# offscreen 必须在导入 PySide6 之前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - 取决于运行环境
    pytest.skip(f"PySide6 不可用：{exc}", allow_module_level=True)

from mihoyo_toolkit.gui import theme, ui_state


@pytest.fixture
def app(tmp_path, monkeypatch):
    """独立的 QApplication（避免与其它测试互相影响）。"""
    monkeypatch.setenv("MIHOYO_HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    (home / "data").mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(
        (Path(__file__).resolve().parents[2] / "config.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    from mihoyo_toolkit.core.config import get_settings
    from mihoyo_toolkit.core.paths import get_path_manager

    get_path_manager.cache_clear()
    get_settings.cache_clear()

    application = QApplication.instance() or QApplication([])
    yield application
    theme.set_mode(theme.DEFAULT_MODE)
    get_path_manager.cache_clear()
    get_settings.cache_clear()


def test_brand_colors_match_mihoyo_site() -> None:
    """浅色调色板使用官网主色与页面底色。"""
    assert theme.LIGHT.primary == "#3778e5"
    assert theme.LIGHT.background == "#f8f9fb"
    assert theme.LIGHT.border == "#e6e7eb"
    assert theme.DARK.background != theme.LIGHT.background


def test_stylesheet_contains_brand_tokens() -> None:
    """样式表包含品牌色、导航胶囊与主按钮变体。"""
    qss = theme.app_stylesheet(theme.LIGHT)
    assert theme.LIGHT.primary in qss
    assert "QListWidget#navList::item:selected" in qss
    assert 'QPushButton[variant="primary"]' in qss
    assert "QFrame#homeCard" in qss


def test_set_mode_normalizes_and_falls_back() -> None:
    """非法模式回退到 auto，合法模式原样返回。"""
    assert theme.set_mode("dark") == "dark"
    assert theme.current_mode() == "dark"
    assert theme.set_mode("light") == "light"
    assert theme.set_mode("nonsense") == theme.DEFAULT_MODE
    assert theme.set_mode("") == theme.DEFAULT_MODE


def test_resolve_mode_returns_palette(monkeypatch) -> None:
    """auto 跟随系统，light/dark 固定。"""
    monkeypatch.setattr(theme, "system_palette", lambda: theme.DARK)
    assert theme.resolve_mode("light") is theme.LIGHT
    assert theme.resolve_mode("dark") is theme.DARK
    assert theme.resolve_mode("auto") is theme.DARK


def test_apply_mode_sets_palette_and_mode(app) -> None:
    """apply_mode 同时切换模式与当前调色板。"""
    applied = theme.apply_mode(app, "dark")
    assert applied is theme.DARK
    assert theme.current_mode() == "dark"
    assert theme.current() is theme.DARK


def test_ui_state_roundtrip(app, tmp_home: Path) -> None:
    """主题模式写入 data/ui_state.json 并可读回。"""
    path = ui_state.save_theme_mode("dark")

    assert path is not None
    assert path == tmp_home / "data" / "ui_state.json"
    assert json.loads(path.read_text(encoding="utf-8"))["theme"] == "dark"
    assert ui_state.load_theme_mode() == "dark"


def test_ui_state_missing_file_returns_default(app, tmp_home: Path) -> None:
    """状态文件缺失时返回默认模式。"""
    assert not ui_state.state_path().exists()
    assert ui_state.load_theme_mode() == theme.DEFAULT_MODE


def test_ui_state_corrupt_file_falls_back(app, tmp_home: Path) -> None:
    """状态文件损坏时回退默认值而不是崩溃。"""
    path = tmp_home / "data" / "ui_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")

    assert ui_state.load_state() == {}
    assert ui_state.load_theme_mode() == theme.DEFAULT_MODE


def test_ui_state_invalid_mode_falls_back(app, tmp_home: Path) -> None:
    """非法主题值回退默认。"""
    path = tmp_home / "data" / "ui_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"theme": "neon"}), encoding="utf-8")

    assert ui_state.load_theme_mode() == theme.DEFAULT_MODE


def test_apply_to_application_does_not_reset_style_each_time(app, monkeypatch) -> None:
    """主题切换不重复调用 setStyle（每次约 350ms 的全量重绘）。"""
    calls: list[str] = []
    monkeypatch.setattr(app, "setStyle", lambda name: calls.append(name), raising=False)
    monkeypatch.setattr(theme, "_style_applied", False)

    theme.apply_to_application(app, theme.LIGHT)
    theme.apply_to_application(app, theme.DARK)
    theme.apply_mode(app, "light")

    assert calls == ["Fusion"]


def test_apply_to_application_can_force_style(app, monkeypatch) -> None:
    """显式 set_style=True 时仍会重新设置样式（上限留给启动路径使用）。"""
    calls: list[str] = []
    monkeypatch.setattr(app, "setStyle", lambda name: calls.append(name), raising=False)
    monkeypatch.setattr(theme, "_style_applied", True)

    theme.apply_to_application(app, theme.LIGHT, set_style=True)

    assert calls == ["Fusion"]
