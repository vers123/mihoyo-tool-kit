# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 米游社工具箱 (miHoYo ToolKit) v2.1.1。

本项目为 **src/ layout**（包体位于 ``src/mihoyo_toolkit``），PyInstaller 以根级
垫片 ``run.py`` 作为分析入口；``pathex`` 同时加入 ``src`` 与仓库根。

支持 onefile / onedir 两种模式，通过环境变量 ``PYI_MODE`` 切换：

* ``set PYI_MODE=onefile``（默认，单文件）
* ``set PYI_MODE=onedir`` （文件夹模式，启动更快）

构建前准备::

    pip install -e ".[dev,pinyin,excel,icon]"
    playwright install chromium

注意：EXE 不打包 Playwright 浏览器，运行时需用户手动执行
``playwright install chromium``。

图标：``resources/icon/app.ico``
版本信息：``version_info.txt``（存在时才注入）
"""

import os

block_cipher = None

# ---- 模式选择 ----
mode = os.environ.get("PYI_MODE", "onefile").lower()
onefile = mode != "onedir"

# ---- 路径 ----
project_root = os.path.abspath(".")
src_dir = os.path.join(project_root, "src")
package_dir = os.path.join(src_dir, "mihoyo_toolkit")
icon_path = os.path.join(project_root, "resources", "icon", "app.ico")
version_file = os.path.join(project_root, "version_info.txt")

# ---- 需要打包的数据文件 ----（不打包 Playwright 浏览器，运行时手动安装）
datas = [
    (os.path.join(project_root, "config.toml"), "."),
    (os.path.join(project_root, "resources"), "resources"),
]

# ---- 隐藏导入（PySide6 / Playwright / 动态 import 的可选依赖）----
hiddenimports = [
    # Playwright（动态加载 driver / 子模块，静态分析无法发现）
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    "playwright._impl",
    # PySide6
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    # 运行时依赖
    "tenacity",
    "httpx",
    "httpcore",
    "h11",
    "certifi",
    "anyio",
    "pydantic",
    "pydantic_settings",
    # 可选依赖（[excel] / [pinyin] / [icon]）
    "openpyxl",
    "tqdm",
    "pypinyin",
    "PIL",
    "PIL.Image",
]

# ---- 自动收集 src/mihoyo_toolkit 下的所有子包（含 __init__.py 的目录）----
if os.path.isdir(package_dir):
    for root_dir, dirs, files in os.walk(package_dir):
        # 跳过缓存目录
        dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
        if "__init__.py" not in files:
            continue
        rel = os.path.relpath(root_dir, src_dir)
        if rel == "mihoyo_toolkit":
            hiddenimports.append("mihoyo_toolkit")
            continue
        module = rel.replace(os.sep, ".")
        hiddenimports.append(module)
else:  # pragma: no cover - 防御性提示
    raise SystemExit(f"未找到包目录: {package_dir}")

a = Analysis(
    ["run.py"],
    pathex=[src_dir, project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pytest",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "IPython",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_args = dict(
    name="米游社工具箱",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if os.path.exists(icon_path):
    exe_args["icon"] = icon_path

if os.path.exists(version_file):
    exe_args["version"] = version_file

if onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        **exe_args,
    )
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_args)
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="米游社工具箱",
    )
