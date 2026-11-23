"""临时文件统一入口（一律使用系统 Temp）。

项目约定：

* 临时文件**只**落在系统临时目录下的本项目专属子目录中，绝不写进仓库；
* 外部文件（如 Firefox ``cookies.sqlite``）先**复制**到临时工作区再解析，源目录保持只读；
* 临时目录使用随机后缀，并发运行的多实例互不干扰；
* 进程被强杀时残留的目录，由下一次启动的 :func:`sweep_stale_temp` 兜底清理。

可用环境变量 ``MIHOYO_TEMP_DIR`` 覆盖临时根（默认 :func:`tempfile.gettempdir`）。
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

#: 临时根覆盖环境变量
TEMP_ENV = "MIHOYO_TEMP_DIR"

#: 本项目临时子目录 / 工作区目录的统一前缀
TEMP_PREFIX = "mihoyo-toolkit-"

#: 视为「陈旧」的默认时长（秒）：24 小时
STALE_AGE_SECONDS = 86400.0


class TempError(RuntimeError):
    """临时目录不可用或无法创建。"""


def temp_root() -> Path:
    """返回临时根目录（保证存在）。

    ``MIHOYO_TEMP_DIR`` 优先，其次系统临时目录。两者都不可写时抛 :class:`TempError`
    —— 静默回退到仓库目录会破坏「仓库不产生临时文件」的约定。
    """
    env_dir = os.environ.get(TEMP_ENV)
    candidates = [Path(env_dir).expanduser()] if env_dir else []
    candidates.append(Path(tempfile.gettempdir()))

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if os.access(candidate, os.W_OK):
            return candidate.resolve()

    raise TempError(
        f"临时目录不可写: {', '.join(str(path) for path in candidates)}"
        f"（可用 {TEMP_ENV} 指定其它目录）"
    )


@contextmanager
def temp_workspace(*, prefix: str = TEMP_PREFIX) -> Iterator[Path]:
    """创建一次性临时工作区，退出时递归删除（异常路径同样清理）。

    用法::

        with temp_workspace() as workdir:
            shutil.copy2(source, workdir / "copy.sqlite")
            ...
    """
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=str(temp_root())))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def sweep_stale_temp(
    *,
    max_age_seconds: float = STALE_AGE_SECONDS,
    prefix: str = TEMP_PREFIX,
    base: Path | None = None,
    keep: Path | None = None,
    now: float | None = None,
) -> int:
    """清理临时根下超龄的本项目目录，返回删除数量。

    只处理以 ``prefix`` 开头且最后修改时间早于 ``max_age_seconds`` 的目录，
    因此不会误删并发运行中的会话（新目录的 mtime 是当前的）。
    """
    search_dir = base if base is not None else temp_root()
    if not search_dir.is_dir():
        return 0

    deadline = (now if now is not None else time.time()) - max_age_seconds
    removed = 0
    for path in search_dir.glob(f"{prefix}*"):
        if keep is not None and path == keep:
            continue
        if not path.is_dir():
            continue
        try:
            if path.stat().st_mtime > deadline:
                continue
        except OSError:
            continue
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            removed += 1
    return removed


__all__ = [
    "STALE_AGE_SECONDS",
    "TEMP_ENV",
    "TEMP_PREFIX",
    "TempError",
    "sweep_stale_temp",
    "temp_root",
    "temp_workspace",
]
