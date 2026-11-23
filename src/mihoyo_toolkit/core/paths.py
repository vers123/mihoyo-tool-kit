"""统一路径管理（PathManager 单例）。

所有运行时目录（data / logs / har / output / resources）均从这里解析，
避免各模块散落 ``os.path.join``。

项目根判定顺序：

1. 环境变量 ``MIHOYO_HOME``（显式覆盖；不可写时直接报错，避免数据「悄悄搬家」）
2. 冻结运行（PyInstaller）→ 可执行文件所在目录
3. 从本文件向上查找含本项目 ``pyproject.toml`` 的目录（源码运行）
4. 当前工作目录（兜底）

自动探测到的根**不可写**时（例如安装在 ``Program Files``），降级到用户数据目录
（Windows ``%LOCALAPPDATA%\\mihoyo-toolkit``），并记录一条告警。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .exceptions import ConfigError
from .temp import temp_root

_HOME_ENV = "MIHOYO_HOME"
_DATA_ENV = "MIHOYO_DATA_DIR"
_APP_DIR_NAME = "mihoyo-toolkit"

#: 教程 HTML 子目录名（位于 ``<root>/data/html`` 下）
TUTORIAL_HTML_SUBDIR = "tutorial"


def is_frozen() -> bool:
    """是否运行在 PyInstaller 等冻结环境中。"""
    return bool(getattr(sys, "frozen", False))


def _has_project_marker(directory: Path) -> bool:
    """目录是否为本项目源码根（``pyproject.toml`` 声明了本项目名）。"""
    marker = directory / "pyproject.toml"
    if not marker.is_file():
        return False
    try:
        import tomllib

        data = tomllib.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    project = data.get("project")
    return isinstance(project, dict) and project.get("name") == "mihoyo-toolkit"


def _detect_project_root() -> Path:
    """按优先级探测项目根目录（不检查可写性）。"""
    env_home = os.environ.get(_HOME_ENV)
    if env_home:
        return Path(env_home).expanduser().resolve()

    if is_frozen():
        return Path(sys.executable).resolve().parent

    # 从本文件向上回溯：core/paths.py -> core -> mihoyo_toolkit -> src -> <root>
    for parent in Path(__file__).resolve().parents:
        if _has_project_marker(parent):
            return parent

    return Path.cwd().resolve()


def app_data_root() -> Path:
    """用户级数据目录（自动探测根不可写时的降级位置）。

    * Windows：``%LOCALAPPDATA%\\mihoyo-toolkit``
    * macOS：``~/Library/Application Support/mihoyo-toolkit``
    * 其它：``$XDG_DATA_HOME/mihoyo-toolkit`` 或 ``~/.local/share/mihoyo-toolkit``
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"
    return (root / _APP_DIR_NAME).resolve()


def _is_writable(directory: Path) -> bool:
    """目录是否可写（不存在时判断其最近的已存在父目录）。"""
    probe = directory
    while True:
        try:
            if probe.exists():
                return os.access(probe, os.W_OK)
        except OSError:  # pragma: no cover - 权限异常
            return False
        if probe.parent == probe:
            return False
        probe = probe.parent


def resolve_root() -> tuple[Path, str | None]:
    """解析项目根并返回 ``(根目录, 降级告警)``。

    ``MIHOYO_HOME`` 显式设置但不可写时抛 :class:`ConfigError`；
    自动探测的根不可写时降级到 :func:`app_data_root` 并返回告警文本。
    """
    root = _detect_project_root()
    if os.environ.get(_HOME_ENV):
        if not _is_writable(root):
            raise ConfigError(
                f"MIHOYO_HOME 指向的目录不可写: {root}",
                detail="请检查目录权限，或改用 MIHOYO_DATA_DIR 指向可写目录",
            )
        return root, None

    if _is_writable(root):
        return root, None

    fallback = app_data_root()
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - 极端环境
        raise ConfigError(
            f"项目根目录不可写且无法创建用户数据目录: {root}",
            detail=str(exc),
        ) from exc

    warning = f"项目根目录不可写，运行时数据已降级到用户目录: {fallback}"
    return fallback, warning


@dataclass(frozen=True, slots=True)
class PathManager:
    """集中式路径解析器（不可变）。"""

    root: Path
    #: 可写数据根目录（默认 <root>/data）
    _data: Path | None = field(default=None, repr=False)
    #: 根目录降级告警（无降级时为 None）
    warning: str | None = None

    @property
    def data(self) -> Path:
        return self._data if self._data is not None else self.root / "data"

    @property
    def html(self) -> Path:
        return self.data / "html"

    @property
    def results(self) -> Path:
        return self.data / "results"

    @property
    def models(self) -> Path:
        return self.data / "models"

    @property
    def db(self) -> Path:
        """SQLite 数据库文件路径。"""
        return self.data / "toolkit.db"

    @property
    def backups(self) -> Path:
        return self.data / "backups"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def har(self) -> Path:
        return self.root / "har"

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def resources(self) -> Path:
        return self.root / "resources"

    @property
    def fonts(self) -> Path:
        return self.resources / "font"

    @property
    def icons(self) -> Path:
        return self.resources / "icon"

    @property
    def config_file(self) -> Path:
        return self.root / "config.toml"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    def har_dir(self, scraper_name: str) -> Path:
        """指定抓取器的 HAR 回退目录。"""
        return self.har / scraper_name

    def ensure_dirs(self) -> None:
        """创建所有运行时目录（幂等）。"""
        for path in (
            self.data,
            self.html,
            self.results,
            self.models,
            self.backups,
            self.logs,
            self.har,
            self.output,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def relative(self, path: Path | str) -> str:
        """返回相对项目根的路径字符串；跨盘符时回退为绝对路径。"""
        target = Path(path).resolve()
        try:
            return str(target.relative_to(self.root))
        except ValueError:
            return str(target)


@lru_cache(maxsize=1)
def get_path_manager() -> PathManager:
    """获取全局 PathManager 单例。"""
    root, warning = resolve_root()
    # 允许通过 MIHOYO_DATA_DIR 覆盖数据目录
    data_env = os.environ.get(_DATA_ENV)
    data = Path(data_env).expanduser().resolve() if data_env else None
    if warning:  # pragma: no cover - 依赖运行环境
        from ..utils.logger import get_module_logger

        get_module_logger("paths").warning(warning)
    return PathManager(root=root, _data=data, warning=warning)


__all__ = [
    "PathManager",
    "TUTORIAL_HTML_SUBDIR",
    "app_data_root",
    "get_path_manager",
    "is_frozen",
    "resolve_root",
    "temp_root",
]
