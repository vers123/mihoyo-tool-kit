# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for 米游社工具箱 (miHoYo ToolKit) v1.2.0

支持 onefile / onedir 两种模式，通过环境变量 PYI_MODE 切换：
  set PYI_MODE=onefile  （单文件，默认）
  set PYI_MODE=onedir   （文件夹模式）

构建前准备：
  1. pip install -r requirements.txt
  2. pip install pyinstaller playwright

注意：EXE 不打包 Playwright 浏览器，运行时需用户手动安装：
  playwright install chromium

图标：resources/icon/app.ico
版本信息：version_info.txt
"""

import os
import sys

block_cipher = None

# ---- 模式选择 ----
mode = os.environ.get("PYI_MODE", "onefile").lower()
onefile = mode == "onefile"

# ---- 路径 ----
project_root = os.path.abspath(".")
icon_path = os.path.join(project_root, "resources", "icon", "app.ico")
version_info = os.path.join(project_root, "version_info.txt")

# ---- 需要打包的数据文件 ----
# 注意：不打包 Playwright 浏览器，运行时由用户手动安装
datas = [
    (os.path.join(project_root, "config.json"), "."),
    (os.path.join(project_root, "resources"), "resources"),
]

# ---- 隐藏导入（PySide6 / Playwright / 动态导入的模块）----
hiddenimports = [
    "playwright",
    "playwright.sync_api",
    "playwright._impl",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "tenacity",
    "httpx",
    "pydantic",
    "openpyxl",
    "tqdm",
    "PIL",
    "PIL.Image",
]

# 收集项目所有子模块
for root_dir, dirs, files in os.walk(project_root):
    # 跳过不需要的目录
    skip = {".venv", ".git", "__pycache__", "browser", "data",
            "logs", "har", "build", "dist", "tests", ".github", "doc"}
    dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]

    rel = os.path.relpath(root_dir, project_root)
    if rel == ".":
        continue
    # 检查是否有 __init__.py
    if "__init__.py" in files:
        module = rel.replace(os.sep, ".")
        hiddenimports.append(module)


a = Analysis(
    ["main.py"],
    pathex=[project_root],
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

if os.path.exists(version_info):
    exe_args["version"] = version_info

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
    exe = EXE(pyz, a.scripts, [], **exe_args)
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
