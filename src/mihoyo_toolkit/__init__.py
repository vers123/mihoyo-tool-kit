"""米游社工具箱 —— 米游社 / 微博 / 米哈游四站点新闻数据抓取与提取工具。

v2.0.0 架构级重构：

* ``core``      —— 配置 / 路径 / 存储 / 模型 / 异常
* ``scrapers``  —— 抓取器（API 优先 + Playwright 回退）
* ``extractors``—— 数据提取
* ``exporters`` —— Excel / RSS / JSON 导出
* ``cli``       —— 命令注册器 + 交互菜单 + argparse
* ``gui``       —— PySide6 Qt MVC 界面
* ``utils``     —— 日志 / HAR / Cookie / 备份 / 迁移 / TXT 过滤
"""

from __future__ import annotations

__version__ = "2.1.3"
__author__ = "LingLan"
__license__ = "MIT"

__all__ = ["__author__", "__license__", "__version__"]
