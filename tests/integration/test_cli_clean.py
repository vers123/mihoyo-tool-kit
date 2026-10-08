"""``system.clean`` 清理命令的集成测试（真实文件 IO）。

重点是 Windows 下的文件占用问题：``logs/app.log`` 被本包 logger 的
``FileHandler`` 持有、``logs/console.log`` 被 ``_TeeStream`` 的镜像持有，
不先释放句柄就删不掉（``WinError 32``）。
"""

from __future__ import annotations

import logging

from mihoyo_toolkit.cli import commands
from mihoyo_toolkit.core import get_path_manager


def test_collect_cache_targets_includes_dev_caches(tmp_home) -> None:
    """构建目录与构建产物文件（与 build.ps1 / build.sh 同口径）都要被收集。"""
    root = get_path_manager().root
    for name in commands.BUILD_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    for name in commands.BUILD_FILES:
        (root / name).write_text("", encoding="utf-8")

    pycache = root / "pkg" / "__pycache__"
    pycache.mkdir(parents=True, exist_ok=True)
    (pycache / "module.pyc").write_bytes(b"")
    # __pycache__ 会整目录删除，故散落在目录之外的 *.pyc 才需要单独收集
    (root / "pkg" / "stray.pyc").write_bytes(b"")

    dirs, files = commands._collect_cache_targets(root)

    assert set(commands.BUILD_DIRS) <= {path.name for path in dirs}
    assert "__pycache__" in {path.name for path in dirs}
    assert set(commands.BUILD_FILES) <= {path.name for path in files}
    assert any(path.suffix == ".pyc" for path in files)


def test_system_clean_deletes_locked_app_log(tmp_home, monkeypatch) -> None:
    """``logs/app.log`` 即使正被本包 logger 持有，也必须能被删除。

    修复前 ``system_clean`` 会打印 ``WinError 32``（另一个程序正在使用此文件）并把
    日志留在原地；该回归在 Windows 上必现。
    """
    logs_dir = tmp_home / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"
    log_file.write_text("", encoding="utf-8")

    holder = logging.getLogger("mihoyo_toolkit.clean_test")
    holder.setLevel(logging.INFO)
    holder.propagate = False
    handler = logging.FileHandler(log_file, encoding="utf-8")
    holder.addHandler(handler)

    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: "YES")
    try:
        commands.system_clean()
    finally:
        holder.removeHandler(handler)
        handler.close()

    assert not log_file.exists()
