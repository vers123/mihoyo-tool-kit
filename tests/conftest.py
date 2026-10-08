"""pytest 全局配置与共享 fixture。

关键隔离策略（务必保持）：

1. 模块导入期即把 ``MIHOYO_HOME`` 指向临时目录，避免测试期间任何
   导入触发的日志 / 目录创建写入仓库（``data`` / ``logs`` / ``har`` / ``output``）。
2. autouse 的 ``_isolated_home`` fixture 为**每个测试**切换到独立 tmp 目录，
   写入最小 ``config.toml``，并清空 ``get_path_manager`` / ``get_settings`` 的
   ``lru_cache`` 与日志 handler。
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import os
import shutil
import tempfile
from pathlib import Path

import pytest

#: 测试用最小配置（对应 core.config.ToolkitSettings）
MINIMAL_CONFIG = """\
[app]
mode = "cli"
version = "2.1.0"

[fetch]
headless = true
wait_seconds = 0.0
timeout = 5000
max_scroll_attempts = 5
scroll_delay = 0.0
user_agent = "mihoyo-toolkit-test-agent"
browser_args = ["--no-sandbox"]

[retry]
max_attempts = 2
delay = 0.0

[incremental]
enabled = true
stop_on_existing = true
merge_data = true

[backup]
enabled = true
max_backups = 3

[cookies]
use_firefox = false

[sources.user]
url = "https://www.miyoushe.com/ys/accountCenter/postList?id=75276539"

[sources.baike]
url = "https://baike.mihoyo.com/ys/obc/channel/map/189/25"

[sources.weibo]
url = "https://weibo.com/u/6593199887"

[sources.news.genshin]
url = "https://ys.mihoyo.com/main/news"
label = "原神"
scraper = "news_genshin"
api_base_url = "https://act-api-takumi-static.mihoyo.com/content_v2_user/app/16471662a82d418a/getContentList"
api_chan_id = "719"
api_page_size = 2
detail_url_pattern = "/main/news/detail/{iInfoId}"
poster_ext_key = "720_1"
lang_subdir = "zh-cn"
expected_total = 4

[sources.news.genshin_en]
url = "https://genshin.hoyoverse.com/en/news"
label = "原神(EN)"
scraper = "news_genshin_en"
api_base_url = "https://sg-public-api-static.hoyoverse.com/content_v2_user/app/a1b1f9d3315447cc/getContentList"
api_app_id = "32"
api_chan_id = "395"
api_page_size = 2
detail_url_pattern = "/en/news/detail/{iInfoId}"
poster_ext_key = "banner"
lang_subdir = "en-us"
expected_total = 2

[sources.news.zzz]
url = "https://zzz.mihoyo.com/news"
label = "绝区零"
scraper = "news_zzz"
api_base_url = "https://api-takumi-static.mihoyo.com/content_v2_user/app/706fd13a87294881/getContentList"
api_chan_id = "273"
api_page_size = 2
detail_url_pattern = "/news/{iInfoId}"
poster_ext_key = "news-banner"
lang_subdir = "zh-cn"
expected_total = 2

[sources.news.starrail]
url = "https://sr.mihoyo.com/news"
label = "星穹铁道"
scraper = "news_starrail"
api_base_url = "https://act-api-takumi-static.mihoyo.com/content_v2_user/app/1963de8dc19e461c/getContentList"
api_chan_id = "255"
api_page_size = 2
detail_url_pattern = "/news/{iInfoId}"
poster_ext_key = "news-poster"
lang_subdir = "zh-cn"
expected_total = 2
"""

#: 测试样例文件目录
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _write_config(home: Path) -> Path:
    """在给定目录写入最小 config.toml。"""
    config = home / "config.toml"
    config.write_text(MINIMAL_CONFIG, encoding="utf-8")
    return config


def reset_caches() -> None:
    """清空路径与配置单例缓存。"""
    from mihoyo_toolkit.core.config import get_settings
    from mihoyo_toolkit.core.paths import get_path_manager

    get_path_manager.cache_clear()
    get_settings.cache_clear()


def reset_logging() -> None:
    """移除 mihoyo_toolkit 相关 logger 的 handler，使日志写入新目录。"""
    import mihoyo_toolkit.utils.logger as logger_module

    for name in list(logging.Logger.manager.loggerDict):
        if not name.startswith("mihoyo_toolkit"):
            continue
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            with contextlib.suppress(Exception):
                handler.close()
            logger.removeHandler(handler)
    logger_module._configured = False


# ---------------------------------------------------------------------- #
#  模块级安全网：任何导入期 IO 都落在会话临时目录，绝不触碰仓库目录
# ---------------------------------------------------------------------- #
_SESSION_HOME = Path(tempfile.mkdtemp(prefix="mihoyo_toolkit_tests_"))
_write_config(_SESSION_HOME)
os.environ["MIHOYO_HOME"] = str(_SESSION_HOME)
reset_caches()
reset_logging()
atexit.register(shutil.rmtree, _SESSION_HOME, ignore_errors=True)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch) -> Path:
    """每个测试使用独立临时项目根（autouse）。"""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    _write_config(home)

    monkeypatch.setenv("MIHOYO_HOME", str(home))
    monkeypatch.delenv("MIHOYO_DATA_DIR", raising=False)
    monkeypatch.delenv("MIHOYO_LEGACY_DIR", raising=False)

    reset_caches()
    reset_logging()

    from mihoyo_toolkit.core.paths import get_path_manager

    get_path_manager().ensure_dirs()

    yield home

    reset_caches()
    reset_logging()


@pytest.fixture
def tmp_home(_isolated_home) -> Path:
    """返回当前测试的临时项目根目录。"""
    return _isolated_home


@pytest.fixture
def settings():
    """返回与临时目录绑定的 ToolkitSettings。"""
    from mihoyo_toolkit.core.config import get_settings

    return get_settings()


@pytest.fixture
def store():
    """返回指向临时数据库的 Storage（默认路径管理器 db）。"""
    from mihoyo_toolkit.core.storage import Storage

    with Storage() as storage:
        yield storage


@pytest.fixture
def sample_news_items():
    """一组新闻条目样例。"""
    from mihoyo_toolkit.core.models import NewsItem

    return [
        NewsItem(
            game="genshin",
            iInfoId=1001,
            sTitle="版本更新说明",
            dtStartTime="2024-01-02 10:00:00",
            sCategoryName="公告",
            sIntro="原神版本更新公告",
            poster_url="https://example.com/poster1.png",
            url="https://ys.mihoyo.com/main/news/detail/1001",
        ),
        NewsItem(
            game="genshin",
            iInfoId=1002,
            sTitle="新角色预告",
            dtStartTime="2024-01-01 09:00:00",
            sCategoryName="资讯",
            sIntro="新角色登场",
            poster_url="",
            url="https://ys.mihoyo.com/main/news/detail/1002",
        ),
    ]


@pytest.fixture
def sample_har_path() -> Path:
    """样例 HAR 文件路径。"""
    return FIXTURES_DIR / "sample.har"


@pytest.fixture
def sample_html_path() -> Path:
    """样例 HTML 文件路径。"""
    return FIXTURES_DIR / "sample_news.html"


@pytest.fixture
def har_factory(tmp_home):
    """把样例 HAR 放入指定 scraper 的 HAR 目录，返回目标路径。"""

    def _factory(scraper_name: str, source: Path | None = None) -> Path:
        from mihoyo_toolkit.utils.har_loader import get_har_dir

        src = source or (FIXTURES_DIR / "sample.har")
        target_dir = get_har_dir(scraper_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "sample.har"
        shutil.copy2(src, target)
        return target

    return _factory
