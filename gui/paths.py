"""GUI 路径工具"""

import os


def get_app_icon_path() -> str:
    """返回应用图标 ICO 的绝对路径"""
    # gui/paths.py → gui/ → 项目根
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "resources", "icon", "app.ico")
