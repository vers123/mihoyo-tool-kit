# 配置管理器不依赖 playwright，无条件导出
from .config_manager import ConfigManager, config_manager

# 抓取基类依赖 playwright，这里做容错顶层导入：
# 好处 1：允许不装 playwright 的环境也能正常 import core.config_manager / 跑 extractors 单元测试
# 好处 2：ZeroTermux 宿主侧即便没装 playwright Python 绑定，也不会在配置阶段就崩
try:
    from .scraper import BaseScraper, ScraperConfig
    _SCRAPER_OK = True
except Exception:  # 包括 ImportError、ModuleNotFoundError、运行时依赖缺失
    BaseScraper = None  # type: ignore
    ScraperConfig = None  # type: ignore
    _SCRAPER_OK = False

__all__ = [
    'BaseScraper',
    'ScraperConfig',
    'ConfigManager',
    'config_manager',
    'SCRAPER_AVAILABLE',
]

# 便于外部代码探测 BaseScraper 是否可用（例如入口依赖检查）
SCRAPER_AVAILABLE = _SCRAPER_OK
