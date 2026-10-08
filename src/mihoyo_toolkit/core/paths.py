"""统一路径管理（PathManager 单例）。

所有运行时目录（data / logs / har / output / resources）均从这里解析，
避免各模块散落 ``os.path.join``。

项目根判定顺序：

1. 环境变量 ``MIHOYO_HOME``（显式覆盖）
2. 从本文件向上查找含 ``pyproject.toml`` 的目录（源码运行）
3. 当前工作目录（已安装为包时的兜底）
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_HOME_ENV = "MIHOYO_HOME"

#: 教程 HTML 子目录名（位于 ``<root>/data/html`` 下）
TUTORIAL_HTML_SUBDIR = "tutorial"


def _detect_project_root() -> Path:
    """按优先级探测项目根目录。"""
    env_home = os.environ.get(_HOME_ENV)
    if env_home:
        return Path(env_home).expanduser().resolve()

    # 从本文件向上回溯：core/paths.py -> core -> mihoyo_toolkit -> src -> <root>
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent

    return Path.cwd().resolve()


@dataclass(frozen=True, slots=True)
class PathManager:
    """集中式路径解析器（不可变）。"""

    root: Path
    #: 可写数据根目录（默认 <root>/data）
    _data: Path | None = field(default=None, repr=False)

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
    root = _detect_project_root()
    # 允许通过 MIHOYO_DATA_DIR 覆盖数据目录
    data_env = os.environ.get("MIHOYO_DATA_DIR")
    data = Path(data_env).expanduser().resolve() if data_env else None
    return PathManager(root=root, _data=data)


__all__ = ["PathManager", "TUTORIAL_HTML_SUBDIR", "get_path_manager"]
