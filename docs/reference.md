# AI Agent 参考手册 · 米游社工具箱 v2.1.2

面向 AI Agent 的**模块 / API 速查表**。所有条目均指向 v2.1.2 公开 API。
导入根：`mihoyo_toolkit`（已安装）或 `python -m mihoyo_toolkit`。

---

## 0. 快速导航

| 需求 | 入口 |
| ------ | ------ |
| 抓取新闻并落库 | `mihoyo_toolkit.scrapers.run_news(game, incremental=True)` |
| 抓取用户发帖 | `mihoyo_toolkit.scrapers.run_user(incremental=False)` |
| 抓取微博 | `mihoyo_toolkit.scrapers.run_weibo(incremental=False)` |
| 读库查询新闻 | `mihoyo_toolkit.core.Storage.query_news(game)` |
| 导出 Excel / RSS / JSON | `mihoyo_toolkit.exporters.export_news_excel / generate_rss_feed / generate_json_feed` |
| 导出 TXT | `mihoyo_toolkit.extractors.run_extract_news(game)` |
| TXT 过滤 | `mihoyo_toolkit.utils.TxtFilter` / `run_filter()` |
| 配置 | `mihoyo_toolkit.core.get_settings()` / `reload_settings()` |
| 路径 | `mihoyo_toolkit.core.get_path_manager()` |
| 日志 | `mihoyo_toolkit.utils.setup_logger()` / `get_module_logger(name)` |

---

## 1. core —— 配置 / 路径 / 存储 / 模型 / 异常

### 1.1 `core.config`

```python
class ToolkitSettings(BaseSettings):        # 根配置（env_prefix="MIHOYO_", nested="__"）
    app: AppSettings
    fetch: FetchSettings
    retry: RetrySettings
    incremental: IncrementalSettings
    backup: BackupSettings
    cookies: CookieSettings
    sources: SourcesSettings                # 必填

def get_settings() -> ToolkitSettings       # lru_cache 单例
def reload_settings() -> ToolkitSettings    # 清缓存并重载
def load_settings(config_file: Path | None = None) -> ToolkitSettings
```

子模型（均为 pydantic `BaseModel`）：

| 模型 | 字段 |
| ------ | ------ |
| `AppSettings` | `mode: "cli"|"gui"`, `version` |
| `FetchSettings` | `headless`, `wait_seconds`, `timeout`, `max_scroll_attempts`, `scroll_delay`, `user_agent`, `browser_args` |
| `RetrySettings` | `max_attempts`, `delay` |
| `IncrementalSettings` | `enabled`, `stop_on_existing`, `merge_data` |
| `BackupSettings` | `enabled`, `max_backups` |
| `CookieSettings` | `use_firefox` |
| `UserSource`/`BaikeSource`/`WeiboSource` | `url` |
| `NewsSiteSource` | `url,label,scraper,api_base_url,api_chan_id,api_page_param,api_page_size_param,api_page_size,api_lang_param,api_lang_value,api_app_id,detail_url_pattern,poster_ext_key,lang_subdir,expected_total` + `detail_url(info_id)` |
| `NewsSources` | `genshin,genshin_en,zzz,starrail: NewsSiteSource` + `keys()`, `get_site(game)` |
| `SourcesSettings` | `user,baike,weibo,news` |

### 1.2 `core.paths`

```python
@dataclass(frozen=True, slots=True)
class PathManager:
    root: Path
    # 属性: data, html, results, images, models, db, backups,
    #       logs, har, output, resources, fonts, icons, config_file, docs
    def har_dir(self, scraper_name: str) -> Path
    def ensure_dirs(self) -> None
    def relative(self, path: Path | str) -> str    # 跨盘符回退绝对路径

def get_path_manager() -> PathManager           # lru_cache 单例
```

> 项目根判定：`MIHOYO_HOME` > 向上查找 `pyproject.toml` > 当前工作目录。

### 1.3 `core.storage`

```python
class Storage:
    def __init__(self, db_path: Path | str | None = None)   # 默认 data/toolkit.db
    # 连接
    def connect() -> sqlite3.Connection
    def close() -> None
    def __enter__() / __exit__()            # 上下文管理器
    # 新闻
    def upsert_news(self, game: str, items: Iterable[NewsItem]) -> int
    def get_existing_urls(self, game: str) -> set[str]
    def get_existing_info_ids(self, game: str) -> set[int]
    def count_news(self, game: str | None = None) -> int
    def count_all(self) -> dict[str, int]   # {game: count}
    def query_news(self, game=None, *, limit=None, ascending=False) -> list[NewsItem]
    # 通用实体
    def upsert_posts(self, items) -> int
    def upsert_weibo(self, items) -> int
    def upsert_tutorial(self, items) -> int
    def upsert_images(self, items) -> int
    def query_posts(self, *, limit=None, ascending=False) -> list[PostItem]
    def query_weibo(self, *, limit=None, ascending=False) -> list[WeiboItem]
    def query_images(self) -> list[ImageItem]
    def get_existing_post_ids(self) -> set[str]
    def get_existing_weibo_ids(self) -> set[str]
    def count_table(self, table: str) -> int       # news|posts|weibo|tutorial|images
    # 维护
    def vacuum() -> None
    def clear(self, game: str | None = None) -> int
```

### 1.4 `core.models`

```python
class NewsItem(BaseModel):    # game, iInfoId:int, sTitle, dtStartTime="", sCategoryName="",
                              # sIntro="", poster_url="", url, raw:dict={}
    # 别名: .info_id, .title, .start_time, .category, .intro ; .sort_key()
class PostItem(BaseModel):    # post_id, title, created_at, url, content
class WeiboItem(BaseModel):   # post_id, text, created_at, url, reposts, comments, attitudes
class TutorialItem(BaseModel):# character_id, name, lang
class ImageItem(BaseModel):   # character_id, name, image_url
class ChangelogEntry(BaseModel):  # version, date, content
ENTITY_TABLES: dict[str, str] # {"news":"news","post":"posts","weibo":"weibo",
                              #  "tutorial":"tutorial","image":"images"}
```

### 1.5 `core.exceptions`

```python
class MihoyoError(Exception):  def __init__(self, message, *, detail: str | None = None)
class ConfigError(MihoyoError)
class NetworkError(MihoyoError)
class RetryExhausted(NetworkError)
class AuthError(NetworkError)
class ParseError(MihoyoError)
class StorageError(MihoyoError)
class ScraperError(MihoyoError)
```

---

## 2. scrapers —— 抓取层

### 2.1 `scrapers.api_client`

```python
class MiHoYoApiClient:
    def __init__(self, game: str, *, incremental=False,
                 existing_urls: set[str] | None = None,
                 site: NewsSiteSource | None = None)
    def build_page_url(self, page: int) -> str
    def headers(self) -> dict[str, str]
    def extract_items(self, data: dict) -> list[NewsItem]
    def fetch_all(self) -> list[NewsItem]          # 同步（httpx + tenacity 重试）
    async def fetch_all_async(self) -> list[NewsItem]

def fetch_all_games(games=None, *, incremental=False, existing_urls_map=None) -> dict[str, list[NewsItem]]
async def fetch_all_games_async(games=None, *, incremental=False, existing_urls_map=None) -> dict[str, list[NewsItem]]
```

### 2.2 `scrapers.base` / `scrapers.browser` / `scrapers.config`

```python
class BaseScraper(ABC, Generic[T]):
    def __init__(self, config: ScrapeConfig)
    @property @abstractmethod
    def name(self) -> str
    @abstractmethod
    def extract_items_from_api(self, data: dict) -> list[Any]
    def parse(self, html: str) -> list[T]
    def setup_api_interception(self, session: BrowserSession) -> None
    def run(self, *, on_progress: Callable[[int], None] | None = None) -> str
    def save_html(self, html: str) -> None
    def check_api_or_har(self) -> str | None        # "use_har" | None

class BrowserSession:
    def __init__(self, config: ScrapeConfig)
    @property page / browser
    def start() -> BrowserSession
    def stop() -> None
    def __enter__() / __exit__()
    def goto(self, url: str | None = None) -> None
    def content(self) -> str
    def scroll_to_bottom(self, *, on_tick=None, is_stopped=None) -> None
    def current_links(self) -> list[str]
def open_browser(config: ScrapeConfig) -> Iterator[BrowserSession]

class ScrapeConfig(BaseModel):
    url, output_filename, scraper_name="", headless=True, wait_seconds=3.0,
    timeout=120000, user_agent="", browser_args=[], scroll_delay=2.0,
    incremental_mode=False, existing_urls=set(), api_url_keywords=[],
    api_domain_filter="", use_firefox_cookies=False, url_selector_template=...
    @classmethod
    def from_settings(cls, url, output_filename, **overrides) -> ScrapeConfig
```

### 2.3 `scrapers.news`

```python
class GameNewsScraper(BaseScraper[NewsItem]):
    game: str = ""
    def __init__(self, game: str | None = None, *, incremental: bool | None = None,
                 site: NewsSiteSource | None = None)
    @property name / html_filename          # html_filename = "{game}_news.html"
    def fetch(self) -> list[NewsItem]        # API → Playwright → HAR
    def fetch_and_store(self) -> int         # 抓取并落库，返回新增条数

def register_news(game: str)                 # 装饰器，注册抓取器
def get_scraper(game: str) -> type[GameNewsScraper]
def run_news(game: str, *, incremental: bool | None = None) -> int
def run_all_news(*, incremental: bool | None = None) -> dict[str, int]
# 子类 / 便捷函数
GenshinNewsScraper / GenshinENNewsScraper / ZZZNewsScraper / SRNewsScraper
run_news_genshin / run_news_genshin_en / run_news_zzz / run_news_starrail
```

### 2.4 其他抓取器

```python
# user
class UserScraper(BaseScraper[PostItem]):  def __init__(self, incremental: bool = False)
def run_user(incremental: bool = False) -> int
# weibo
class WeiboScraper(BaseScraper[WeiboItem]): def __init__(self, incremental: bool = False)
def run_weibo(incremental: bool = False) -> int
# baike
class BaikeScraper(BaseScraper[ImageItem]): def __init__(self)
def run_baike() -> int
# tutorial
class TutorialScraper(BaseScraper[TutorialItem]): def __init__(self, tutorial_id, lang=None)
def run_tutorial(tutorial_id: str, lang: str | None = None) -> None
def run_tutorial_batch(index_id: str, lang: str | None = None) -> int
# custom
class CustomScraper(BaseScraper[str]): def __init__(self, url, output_filename="custom_page.html")
def run_custom(url: str, filename: str = "custom_page.html") -> None
# model_downloader
def run_model_download() -> int
def parse_create_plan(plan_path=None) -> list[VersionInfo]
def extract_download_links_from_html(html: str, page_url: str = "") -> list[dict]
def fetch_page_html(url: str) -> str
def download_file(url: str, save_path: Path, timeout: float = 300.0) -> bool
```

---

## 3. extractors —— 提取层（读库 → TXT）

```python
# news
class GameNewsBaseExtractor:
    game: str = ""
    def __init__(self, game: str | None = None, *, db_path=None)
    @property output_path -> Path                # data/results/{game}_news.txt
    def load_news(self, *, limit=None) -> list[NewsItem]
    def extract_news(self, incremental=False, *, limit=None) -> list[NewsItem]
    @staticmethod
    def format_line(index: int, item: NewsItem) -> str
    def save_news_data(self, items) -> Path
    def export(self, *, incremental=False) -> Path | None
GenshinNewsExtractor / GenshinENNewsExtractor / ZZZNewsExtractor / SRNewsExtractor
def run_extract_news(game: str, incremental: bool = False) -> None

# posts / weibo / images
class PostExtractor:  def __init__(self, topic="posts", *, db_path=None)
class WeiboExtractor: def __init__(self, topic="weibo", *, db_path=None)
class ImageExtractor: def __init__(self, topic="images", *, db_path=None)
def run_extract_posts(incremental: bool = False) -> None
def run_extract_weibo(incremental: bool = False) -> None
def run_extract_images() -> None

# tutorial（保留 HTML 解析）
class TutorialExtractor:  def __init__(self, tutorial_id, lang=None, ...)
class ChangelogExtractor: def __init__(self, tutorial_id, lang=None, ...)
def run_extract_tutorial(tutorial_id: str, lang: str | None = None) -> None
```

> `output_path` 约定：新闻 `{game}_news.txt`；发帖 `posts.txt`；微博 `weibo.txt`。

---

## 4. exporters —— 导出层

```python
class ExcelWriter:
    def __init__(self, output_path=None, *, db_path=None)   # 默认 output/news.xlsx
    def export(self) -> Path
def export_news_excel() -> Path

class FeedGenerator:
    def __init__(self, rss_path=None, json_path=None, *, db_path=None)
    def write_rss(self) -> Path        # output/news_feed.xml
    def write_json(self) -> Path       # output/news_feed.json
def generate_rss_feed() -> Path
def generate_json_feed() -> Path
```

> Excel 依赖 `openpyxl`（懒加载）；`pip install "mihoyo-toolkit[excel]"`。

---

## 5. cli —— 命令行

```python
# registry
@dataclass(slots=True)
class Command: key, label, description, group, handler, order=0

class CommandRegistry:
    def register(self, *, key, label, description, group, order=0) -> Callable[[F], F]
    def get(self, key: str) -> Command                 # 未注册抛 KeyError
    def all(self) -> list[Command]
    def by_group(self) -> dict[str, list[Command]]     # 组内按 order 排序
registry: CommandRegistry                              # 模块级单例

# menu
class Menu:
    def __init__(self, commands: CommandRegistry | None = None)
    def run(self) -> None

# commands（导入即注册全部 43 项命令）
NEWS_GROUPS: dict[str, str]    # {"genshin":"原神新闻", ...}
```

**入口**：

```python
mihoyo_toolkit.__main__.main(argv: Sequence[str] | None = None) -> int    # 返回退出码
mihoyo_toolkit.__main__.gui_main() -> None                                # gui-scripts
```

---

## 6. gui —— 图形界面（需要 PySide6）

```python
def launch_gui() -> None                     # 创建 QApplication + 主窗口 + 事件循环
class MainWindow(QMainWindow):
    nav_entries: list[NavEntry]              # 由命令注册表派生的导航项
    def __init__(self, fonts: dict[str, str] | None = None, parent=None)

def build_nav(reg: CommandRegistry | None = None) -> list[NavEntry]
@dataclass(frozen=True)
class NavEntry:                              # key / title / commands / factory

class TaskController(QObject):
    started / progress(int) / message(str) / finished(object) / failed(str) / cancelled
    @property is_running -> bool
    def run(self, func, *args, label="任务", **kwargs) -> bool
    def stop(self) -> None
    def report_progress(self, percent: int) -> None
    def report_message(self, text: str) -> None

class SystemController(QObject):
    def list_backups(self) -> list[BackupInfo]
    def latest_database_backup(self) -> BackupInfo | None
    def restore_database_backup(self, info: BackupInfo) -> bool
    def read_config_text(self) -> str
    def write_config_text(self, text: str) -> None
    def reload_config(self) -> object
    def system_info(self) -> list[str]
    def migrate(self) -> None
    def cleanup(self) -> list[str]

class TaskWorker(QThread):
    progress(int) / message(str) / finished_ok(object) / failed(str) / cancelled
    def __init__(self, func, *args, label="任务", parent=None, **kwargs)
    def request_cancellation(self) -> None
class TaskCancelledError(Exception)

class BasePage(QWidget):
    log_message = Signal(str)
    def run_task(self, func, label, *args, **kwargs) -> bool
    def stop_task(self) -> None
    def reload_table(self) -> None
    # 控件工厂: make_header / make_button / make_stop_row / make_table / register_buttons
```

---

## 7. utils —— 工具层

```python
# logger
def setup_console_log() -> None            # stdout/stderr → logs/console.log
def setup_logger(name="mihoyo_toolkit", level=logging.INFO) -> logging.Logger  # → logs/app.log
def get_module_logger(name: str) -> logging.Logger
def append_gui_log(message: str) -> None   # → logs/gui.log
def log_function_call(func) -> func        # 装饰器

# har_loader
def get_har_dir(scraper_name: str) -> Path
def ensure_har_dirs() -> None
def find_har_file(scraper_name: str) -> Path | None
def parse_har_file(har_path) -> list[dict]
def load_har_entries(scraper_name: str) -> list[dict]     # 全部 JSON 响应体
def extract_api_patterns(har_path, domain_keywords=None) -> list[dict]
def load_api_pattern_from_har(scraper_name, domain_keywords=None) -> dict | None
def print_har_instructions(scraper_name, page_url, domain_keywords=None) -> None
def get_har_welcome_text() -> str
def get_har_welcome_html() -> str

# cookie_loader
def find_firefox_profile() -> Path | None
def load_firefox_cookies(domain_filter: str | None = None) -> list[dict]

# backup_manager
class BackupInfo(BaseModel): ...          # filename / filepath / created_at / size
class BackupManager:
    @property backup_dir -> Path
    @property max_backups -> int
    def backup_file(self, source: Path, *, reason="") -> BackupInfo | None
    def backup_database(self) -> BackupInfo | None
    def list_backups(self, filename: str) -> list[BackupInfo]
    def restore_backup(self, backup_path: Path, target_path: Path) -> bool
    def prune(self, max_backups: int) -> int
backup_manager: BackupManager             # 单例

# migration
class DataMigrationManager:
    def __init__(self, legacy_dir: Path | None = None)
    def needs_migration(self) -> bool
    def run_migration(self) -> dict
def check_and_migrate() -> None

# txt_filter
class MatchResult(BaseModel): line_no, timestamp, text, matched_keywords, source_file
class TxtFilter:
    def __init__(self, output_root: Path | None = None)
    @property output_dir -> Path                      # data/results/filtered
    def list_txt_files(self) -> list[tuple[str, Path, int]]
    @staticmethod
    def parse_timestamp(line: str) -> str
    @classmethod
    def match_keywords(cls, text, keywords, *, fuzzy=False) -> list[str]
    def filter_text(self, text, keywords, *, fuzzy=False, ascending=False, source_file="") -> list[MatchResult]
    def filter_file(self, path, keywords, *, fuzzy=False, ascending=False) -> list[MatchResult]
    def export(self, results, dest: Path) -> Path
def run_filter() -> None
```

---

## 8. 常见任务配方

### 8.1 只抓取新闻，不启动浏览器

```python
from mihoyo_toolkit.scrapers import run_news

# 单站点增量抓取（API 直连 httpx，仅在 API 失败时才启动浏览器）
new = run_news("genshin", incremental=True)
print(new)

# CLI 等价
# mihoyo-toolkit --fetch genshin
```

### 8.2 抓取全部站点并查看条数

```python
from mihoyo_toolkit.scrapers import run_all_news
from mihoyo_toolkit.core import Storage

run_all_news(incremental=True)
with Storage() as store:
    print(store.count_all())
# CLI: mihoyo-toolkit --fetch all --count
```

### 8.3 导出 Excel

```python
from mihoyo_toolkit.exporters import export_news_excel

path = export_news_excel()  # output/news.xlsx，每站点一个 sheet
print(path)
# CLI: mihoyo-toolkit --export-excel
# 需先 pip install "mihoyo-toolkit[excel]"
```

### 8.4 导出 RSS / JSON Feed

```python
from mihoyo_toolkit.exporters import generate_rss_feed, generate_json_feed

generate_rss_feed()  # output/news_feed.xml
generate_json_feed()  # output/news_feed.json
# CLI: mihoyo-toolkit --export-feed rss|json
```

### 8.5 导出新闻 TXT

```python
from mihoyo_toolkit.extractors import run_extract_news

run_extract_news("genshin")  # data/results/genshin_news.txt
run_extract_news("starrail")
```

### 8.6 批量过滤 TXT

```python
from pathlib import Path
from mihoyo_toolkit.utils import TxtFilter

flt = TxtFilter()
files = flt.list_txt_files()  # [(相对路径, Path, 行数)]
results = []
for _rel, path, _n in files:
    results.extend(flt.filter_file(path, ["原神", "绝区零"], fuzzy=True, ascending=False))
out = flt.export(results, flt.output_dir)  # data/results/filtered/...
print(out)
# CLI: mihoyo-toolkit --filter （交互式）
```

### 8.7 直接读库查询

```python
from mihoyo_toolkit.core import Storage

with Storage() as store:
    items = store.query_news("genshin", limit=20)  # 默认时间倒序
    for item in items:
        print(item.start_time, item.title, item.url)
    print("tutorial:", store.count_table("tutorial"))
```

### 8.8 修改配置并重载

```python
from mihoyo_toolkit.core import get_settings, reload_settings

settings = get_settings()
print(settings.fetch.headless)
# 环境变量覆盖（进程级）：设置 MIHOYO_FETCH__HEADLESS=false 后：
settings = reload_settings()
print(settings.fetch.headless)
```

### 8.9 手动 HAR 回退

```python
from mihoyo_toolkit.utils import find_har_file, load_har_entries

# 将导出的 HAR 放入 har/news_genshin/ 后：
har = find_har_file("news_genshin")
payloads = load_har_entries("news_genshin")  # 全部 JSON 响应体（可直接喂给 extract_items）
```

### 8.10 新增一条自定义命令

```python
# 在 mihoyo_toolkit.cli.commands 中追加
from mihoyo_toolkit.cli.registry import registry


@registry.register(
    key="custom.hello",
    label="示例命令",
    description="演示用命令",
    group="系统工具",
    order=99,
)
def hello() -> None:
    print("hello")
```

### 8.11 后台线程执行任务（GUI）

```python
from mihoyo_toolkit.gui.controllers import TaskController
from mihoyo_toolkit.scrapers import run_news

ctrl = TaskController()
ctrl.finished.connect(lambda r: print("完成", r))
ctrl.message.connect(print)
ctrl.run(lambda: run_news("genshin", incremental=True), label="抓取原神新闻")
```

---

## 9. 环境变量速查

| 变量 | 作用 |
| ------ | ------ |
| `MIHOYO_HOME` | 覆盖项目根目录 |
| `MIHOYO_DATA_DIR` | 覆盖数据目录（默认 `<root>/data`） |
| `MIHOYO_FETCH__HEADLESS` | 覆盖 `[fetch].headless` |
| `MIHOYO_FETCH__WAIT_SECONDS` | 覆盖 `[fetch].wait_seconds` |
| `MIHOYO_RETRY__MAX_ATTEMPTS` | 覆盖 `[retry].max_attempts` |
| `MIHOYO_INCREMENTAL__STOP_ON_EXISTING` | 覆盖 `[incremental].stop_on_existing` |
| `MIHOYO_COOKIES__USE_FIREFOX` | 覆盖 `[cookies].use_firefox` |
| `MIHOYO_SOURCES__USER__URL` | 覆盖 `[sources.user].url` |
| `PYI_MODE` | PyInstaller 打包模式：`onefile`（默认）/ `onedir` |
