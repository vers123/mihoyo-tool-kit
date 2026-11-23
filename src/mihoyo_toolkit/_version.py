"""版本号解析（单一来源：``pyproject.toml``）。

本模块刻意不导入包内任何其它模块，避免 ``mihoyo_toolkit/__init__`` 出现循环依赖。

解析顺序：

1. **源码运行** —— 向上查找声明本项目名的 ``pyproject.toml``，读取 ``[project].version``；
2. **安装 / 冻结运行** —— 读取已安装包的元数据（PyInstaller 通过
   ``copy_metadata`` 一并打包，见 ``app.spec``）；
3. 两者都不可用时返回 :data:`UNKNOWN_VERSION`，**不抛异常**（版本号缺失不应让程序启动失败）。
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

#: 包名（用于元数据查询与 ``pyproject.toml`` 校验）
PROJECT_NAME = "mihoyo-toolkit"

#: 无法解析版本时的占位值
UNKNOWN_VERSION = "0.0.0+unknown"


def read_pyproject_version(directory: Path) -> str | None:
    """读取目录下 ``pyproject.toml`` 的版本；不是本项目或文件损坏时返回 ``None``。"""
    candidate = Path(directory) / "pyproject.toml"
    if not candidate.is_file():
        return None
    try:
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # TOMLDecodeError 是 ValueError 的子类；损坏的 pyproject 不应中断导入
        return None
    project = data.get("project")
    if not isinstance(project, dict) or project.get("name") != PROJECT_NAME:
        return None
    version = project.get("version")
    return version if isinstance(version, str) and version else None


def _source_version() -> str | None:
    """从源码树的 ``pyproject.toml`` 读取版本；找不到或不是本项目时返回 ``None``。"""
    for parent in Path(__file__).resolve().parents:
        version = read_pyproject_version(parent)
        if version is not None:
            return version
    return None


def _installed_version() -> str | None:
    """读取已安装包的元数据版本；未安装时返回 ``None``。"""
    import importlib.metadata as metadata

    try:
        return metadata.version(PROJECT_NAME)
    except metadata.PackageNotFoundError:
        return None
    except Exception:  # pragma: no cover - 元数据损坏等极端情况
        return None


@lru_cache(maxsize=1)
def get_version() -> str:
    """返回当前运行环境的版本号（源码优先，其次安装元数据，最后占位值）。"""
    return _source_version() or _installed_version() or UNKNOWN_VERSION


__all__ = ["PROJECT_NAME", "UNKNOWN_VERSION", "get_version", "read_pyproject_version"]
