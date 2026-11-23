"""版本号解析测试（单一来源：pyproject.toml）。"""

from __future__ import annotations

from pathlib import Path

import mihoyo_toolkit
from mihoyo_toolkit._version import PROJECT_NAME, UNKNOWN_VERSION, get_version


def test_version_matches_pyproject() -> None:
    """源码运行时应读到 pyproject.toml 的版本，而不是过期的安装元数据。"""
    import tomllib

    root = Path(mihoyo_toolkit.__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert mihoyo_toolkit.__version__ == data["project"]["version"]
    assert get_version() == data["project"]["version"]


def test_version_from_metadata_when_no_source_tree(monkeypatch) -> None:
    """源码树不可用时回退到已安装包的元数据。"""
    monkeypatch.setattr("mihoyo_toolkit._version._source_version", lambda: None)
    monkeypatch.setattr("mihoyo_toolkit._version._installed_version", lambda: "9.9.9")
    get_version.cache_clear()
    try:
        assert get_version() == "9.9.9"
    finally:
        get_version.cache_clear()


def test_version_falls_back_to_unknown(monkeypatch) -> None:
    """两者都不可用时返回占位值，不抛异常。"""
    monkeypatch.setattr("mihoyo_toolkit._version._source_version", lambda: None)
    monkeypatch.setattr("mihoyo_toolkit._version._installed_version", lambda: None)
    get_version.cache_clear()
    try:
        assert get_version() == UNKNOWN_VERSION
    finally:
        get_version.cache_clear()


def test_read_pyproject_version_ignores_foreign_project(tmp_path: Path) -> None:
    """只认声明了本项目名的 pyproject.toml。"""
    from mihoyo_toolkit._version import read_pyproject_version

    foreign = tmp_path / "pyproject.toml"
    foreign.write_text('[project]\nname = "other"\nversion = "1.0.0"\n', encoding="utf-8")
    assert read_pyproject_version(tmp_path) is None


def test_read_pyproject_version_handles_broken_toml(tmp_path: Path) -> None:
    """损坏的 pyproject.toml 不抛异常，返回 None。"""
    from mihoyo_toolkit._version import read_pyproject_version

    (tmp_path / "pyproject.toml").write_text("not = [valid", encoding="utf-8")
    assert read_pyproject_version(tmp_path) is None


def test_read_pyproject_version_reads_matching_project(tmp_path: Path) -> None:
    """本项目名 + 版本号正确返回。"""
    from mihoyo_toolkit._version import read_pyproject_version

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "mihoyo-toolkit"\nversion = "4.2.0"\n', encoding="utf-8"
    )
    assert read_pyproject_version(tmp_path) == "4.2.0"


def test_project_name_constant() -> None:
    """包名常量与 pyproject 一致，避免元数据查询落空。"""
    assert PROJECT_NAME == "mihoyo-toolkit"
