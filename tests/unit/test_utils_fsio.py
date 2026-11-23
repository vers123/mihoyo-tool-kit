"""utils.fsio 单元测试（原子写入 + 工作区边界）。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mihoyo_toolkit.core.exceptions import StorageError
from mihoyo_toolkit.utils.fsio import (
    atomic_save,
    atomic_write_bytes,
    atomic_write_text,
    ensure_writable_location,
    is_writable_location,
)


def _outside_path(name: str = "denied.txt") -> Path:
    """构造一个跨平台都位于「工作区与临时根之外」的路径。

    取系统临时目录的**父目录**：Windows 下是 ``%LOCALAPPDATA%``，Linux 下是 ``/``，
    两者都不会落在工作区或临时根内（且测试只校验拒绝，不会真正写盘）。
    """
    return Path(tempfile.gettempdir()).resolve().parent / "__mihoyo_outside__" / name


def test_is_writable_location_inside_root(tmp_home: Path) -> None:
    """工作区内路径允许写入。"""
    assert is_writable_location(tmp_home / "data" / "a.txt")
    assert is_writable_location(tmp_home)


def test_is_writable_location_allows_temp_root(tmp_home: Path, tmp_path: Path) -> None:
    """临时根内同样允许写入（外部文件先复制到此处理）。"""
    assert is_writable_location(tmp_path / "scratch.txt")


def test_is_writable_location_rejects_outside(tmp_home: Path) -> None:
    """工作区与临时根之外一律拒绝。"""
    assert not is_writable_location(_outside_path("hosts"))


def test_ensure_writable_location_raises_storage_error(tmp_home: Path) -> None:
    """越界写入的异常类型与提示都要明确。"""
    with pytest.raises(StorageError) as excinfo:
        ensure_writable_location(_outside_path())
    assert "工作区外只读" in str(excinfo.value)


def test_atomic_write_text_is_lf_only(tmp_home: Path) -> None:
    """写入使用 LF，不受平台换行翻译影响。"""
    target = tmp_home / "data" / "lf.txt"
    atomic_write_text(target, "a\nb\n")
    assert target.read_bytes() == b"a\nb\n"


def test_atomic_write_text_creates_parent_dirs(tmp_home: Path) -> None:
    """父目录不存在时自动创建。"""
    target = tmp_home / "data" / "deep" / "nested" / "f.txt"
    atomic_write_text(target, "x")
    assert target.read_text(encoding="utf-8") == "x"


def test_atomic_write_text_replaces_existing(tmp_home: Path) -> None:
    """覆盖写入后内容为新值，且不残留临时文件。"""
    target = tmp_home / "data" / "replace.txt"
    target.write_text("old", encoding="utf-8")
    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"
    leftovers = [p for p in target.parent.iterdir() if p.name.startswith(f".{target.name}.")]
    assert leftovers == []


def test_atomic_write_text_keeps_original_on_failure(tmp_home: Path) -> None:
    """写入中途失败时原文件不被破坏。"""
    target = tmp_home / "data" / "keep.txt"
    target.write_text("original", encoding="utf-8")

    def _boom(handle) -> None:
        handle.write("partial")
        raise OSError("disk full")

    with pytest.raises(StorageError):
        from mihoyo_toolkit.utils import fsio

        fsio._atomic_write(target, _boom, binary=False)

    assert target.read_text(encoding="utf-8") == "original"


def test_atomic_write_bytes(tmp_home: Path) -> None:
    """二进制写入内容一致。"""
    target = tmp_home / "data" / "blob.bin"
    atomic_write_bytes(target, b"\x00\x01")
    assert target.read_bytes() == b"\x00\x01"


def test_atomic_save_uses_temp_then_replaces(tmp_home: Path) -> None:
    """第三方保存函数收到临时路径，最终目标是同一份内容。"""
    target = tmp_home / "output" / "feed.bin"
    seen: list[Path] = []

    def _save(path: Path) -> None:
        seen.append(path)
        path.write_bytes(b"saved")

    atomic_save(target, _save)
    assert target.read_bytes() == b"saved"
    assert seen and seen[0] != target


def test_atomic_save_wraps_oserror(tmp_home: Path) -> None:
    """保存失败统一包装为 StorageError。"""
    target = tmp_home / "output" / "bad.bin"

    def _save(path: Path) -> None:
        raise OSError("no space")

    with pytest.raises(StorageError):
        atomic_save(target, _save)
    assert not target.exists()


def test_atomic_write_rejects_outside_path(tmp_home: Path) -> None:
    """越界写入在落盘前就被拒绝。"""
    with pytest.raises(StorageError):
        atomic_write_text(_outside_path(), "x")
