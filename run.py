"""PyInstaller 入口垫片（src/ layout 适配）。

本项目采用 src/ layout，包本体位于 ``src/mihoyo_toolkit``。PyInstaller 需要
一个「根级脚本」作为分析入口，故在此提供垫片：

1. 将 ``src/`` 注入 ``sys.path``（源码运行 / 非可编辑安装时定位包）；
2. 转发到 ``mihoyo_toolkit.__main__:main`` 并以其返回值作为退出码。

等价于已安装后的控制台脚本 ``mihoyo-toolkit``。
"""

from __future__ import annotations

import sys
from pathlib import Path

# src/ layout：把仓库根的 src/ 加入模块搜索路径（幂等）。
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mihoyo_toolkit.__main__ import main  # noqa: E402

raise SystemExit(main())
