"""统一文件写入层（原子替换 + 统一编码/换行 + 工作区边界校验）。

设计目标：

1. **不产生半截文件** —— 先写同目录临时文件再 ``os.replace``，写入失败时原文件保持原样；
   临时文件与目标同目录，避免跨盘 ``EXDEV``。
2. **编码与换行稳定** —— 默认 UTF-8 + ``\\n``，不受平台影响
   （``Path.write_text`` 在 Windows 上会把 ``\\n`` 翻成 CRLF）。
3. **工作区外只读** —— :func:`ensure_writable_location` 只放行「项目根内」与「临时根内」，
   其它位置抛 :class:`~mihoyo_toolkit.core.exceptions.StorageError`，提示先复制到工作区。
4. **异常类型统一** —— ``OSError`` 一律包装成 :class:`~mihoyo_toolkit.core.exceptions.StorageError`，
   CLI / GUI 只需捕获项目异常即可。
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

from ..core.exceptions import StorageError
from ..core.temp import temp_root

#: 写入时的默认编码
DEFAULT_ENCODING = "utf-8"

#: 写入时的默认换行符（显式指定，避免 Windows 上被翻译为 CRLF）
DEFAULT_NEWLINE = "\n"

#: 临时文件后缀（与目标同目录，便于 ``os.replace`` 原子替换）
_TMP_SUFFIX = ".tmp"


def _resolve(path: Path | str) -> Path:
    """解析为绝对路径（不要求文件存在）。"""
    return Path(path).expanduser().resolve()


def _writable_roots() -> tuple[Path, ...]:
    """返回允许写入的根目录（项目根 + 临时根），延迟解析以支持测试切换环境。"""
    from ..core.paths import get_path_manager

    roots: list[Path] = [get_path_manager().root]
    with suppress(Exception):
        # 临时根不可用时只保留项目根，越界写入仍会被拒
        roots.append(temp_root())
    return tuple(roots)


def is_writable_location(path: Path | str) -> bool:
    """判断路径是否位于允许写入的区域（项目根或临时根之内）。"""
    target = _resolve(path)
    return any(target == root or target.is_relative_to(root) for root in _writable_roots())


def ensure_writable_location(path: Path | str) -> Path:
    """校验写入位置；越界时抛 :class:`StorageError`，合法时返回解析后的路径。"""
    target = _resolve(path)
    if not is_writable_location(target):
        raise StorageError(
            f"拒绝写入工作区外路径: {target}",
            detail="工作区外只读：请先复制到工作区或临时目录后再写入",
        )
    return target


def _atomic_write(
    path: Path | str,
    writer: Callable[[Any], None],
    *,
    binary: bool,
    encoding: str = DEFAULT_ENCODING,
    newline: str | None = DEFAULT_NEWLINE,
) -> Path:
    """通用原子写入：同目录临时文件 → 落盘 → 替换目标。"""
    target = ensure_writable_location(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp_name: str | None = None
    try:
        if binary:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(target.parent),
                prefix=f".{target.name}.",
                suffix=_TMP_SUFFIX,
                delete=False,
            ) as handle:
                tmp_name = handle.name
                writer(handle)
        else:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(target.parent),
                prefix=f".{target.name}.",
                suffix=_TMP_SUFFIX,
                delete=False,
                encoding=encoding,
                newline=newline,
            ) as handle:
                tmp_name = handle.name
                writer(handle)
        os.replace(tmp_name, target)
        tmp_name = None
    except OSError as exc:
        raise StorageError(f"写入文件失败: {target}", detail=str(exc)) from exc
    finally:
        if tmp_name is not None:
            with suppress(OSError):
                os.unlink(tmp_name)
    return target


def atomic_write_text(
    path: Path | str,
    text: str,
    *,
    encoding: str = DEFAULT_ENCODING,
    newline: str | None = DEFAULT_NEWLINE,
) -> Path:
    """原子写入文本（默认 UTF-8 + ``\\n``），返回目标路径。"""
    return _atomic_write(
        path,
        lambda handle: handle.write(text),
        binary=False,
        encoding=encoding,
        newline=newline,
    )


def atomic_write_bytes(path: Path | str, data: bytes) -> Path:
    """原子写入二进制内容，返回目标路径。"""
    return _atomic_write(path, lambda handle: handle.write(data), binary=True)


def atomic_save(path: Path | str, save_fn: Callable[[Path], None]) -> Path:
    """配合「先写文件再返回」的第三方库（如 ``openpyxl.Workbook.save``）做原子保存。

    ``save_fn`` 收到的是同目录临时文件路径；写成功后再原子替换目标。
    """
    target = ensure_writable_location(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # 用 mkstemp 预留唯一路径后立即关闭句柄，把写入完全交给 save_fn
    handle, tmp_name = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=_TMP_SUFFIX,
    )
    os.close(handle)
    tmp_path = Path(tmp_name)

    try:
        save_fn(tmp_path)
        os.replace(tmp_path, target)
    except OSError as exc:
        raise StorageError(f"写入文件失败: {target}", detail=str(exc)) from exc
    finally:
        with suppress(OSError):
            tmp_path.unlink(missing_ok=True)
    return target


__all__ = [
    "DEFAULT_ENCODING",
    "DEFAULT_NEWLINE",
    "atomic_save",
    "atomic_write_bytes",
    "atomic_write_text",
    "ensure_writable_location",
    "is_writable_location",
]
