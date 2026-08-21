PROJECT_INTRODUCTION_AI_V1
SCHEMA_VERSION: 1.0
GENERATED_AT: 2026-08-21T00:00:00Z
DOC_LANGUAGE: zh-CN

================================================================================
SECTION_00: PROJECT_META
================================================================================
{
  "project_name": "miHoYo_ToolKit",
  "project_name_cn": "米游社工具箱",
  "repo_url": "https://github.com/vers123/miHoYo_ToolKit.git",
  "code_version_in_main_py": "2.1.0",
  "release_version_in_readme": "RV1.0.0",
  "license": "MIT",
  "license_copyright_year": 2026,
  "license_copyright_holder": "昤兰(LingLan)",
  "program_language": "Python",
  "language_min_version": "3.8",
  "runtime_mode": "CLI_interactive_menu",
  "main_executable": "main.py",
  "main_class": "MiHoYoToolKit",
  "main_function": "main()",
  "exit_code_0_behavior": "graceful_exit",
  "total_menu_items": 23,
  "dependency_count_requirements_txt": 1,
  "dependencies": [
    {"package": "playwright", "version_constraint": ">=1.40.0", "browser_driver_required": "chromium"}
  ],
  "codebase_loc_estimate": 2200,
  "python_source_files": [
    "main.py",
    "core/__init__.py",
    "core/scraper.py",
    "core/config_manager.py",
    "fetchers/__init__.py",
    "fetchers/user.py",
    "fetchers/baike.py",
    "fetchers/news.py",
    "fetchers/weibo.py",
    "fetchers/tutorial.py",
    "fetchers/custom.py",
    "extractors/__init__.py",
    "extractors/time.py",
    "extractors/news.py",
    "extractors/weibo.py",
    "extractors/images.py",
    "extractors/tutorial.py",
    "utils/__init__.py",
    "utils/logger.py",
    "utils/error_handler.py",
    "utils/backup_manager.py",
    "utils/cookie_loader.py",
    "utils/har_loader.py",
    "tests/__init__.py",
    "tests/test_extractors.py"
  ],
  "non_source_files": [
    "README.md",
    "LICENSE",
    "requirements.txt",
    "config.json",
    ".gitignore"
  ]
}

================================================================================
SECTION_01: FILESYSTEM_LAYOUT
================================================================================
ROOT: /workspace
ENTRIES:
- DIR core/
  - FILE __init__.py [size_class: small]
    - PUBLIC_EXPORTS: ["BaseScraper", "ScraperConfig", "ConfigManager", "config_manager"]
    - IMPORTS: [".scraper", ".config_manager"]
  - FILE scraper.py [size_class: large, lines: 249]
    - PUBLIC_CLASSES: ["ScraperConfig(dataclass)", "BaseScraper"]
    - IMPORTS: ["playwright.sync_api:sync_playwright,Page,Browser", "os", "time",
                "typing:Dict,Any,Set,Optional,List,Callable", "dataclasses:dataclass,field",
                ".config_manager:config_manager",
                "utils.cookie_loader:load_firefox_cookies",
                "utils.har_loader:find_har_file,load_api_pattern_from_har,print_har_instructions"]
  - FILE config_manager.py [size_class: large, lines: 186]
    - PUBLIC_CLASSES: ["OutputDirs(dataclass)", "Filenames(dataclass)",
                       "ScrollSettings(dataclass)", "RetrySettings(dataclass)",
                       "IncrementalSettings(dataclass)", "BackupSettings(dataclass)",
                       "ConfigManager"]
    - PUBLIC_SINGLETONS: ["config_manager:ConfigManager"]
    - IMPORTS: ["json", "os", "typing:Dict,Any,Optional", "dataclasses:dataclass,asdict"]
- DIR fetchers/
  - FILE __init__.py [size_class: small]
    - PUBLIC_EXPORTS: ["UserScraper","BaikeScraper","NewsScraper","TutorialScraper",
                       "CustomScraper","WeiboScraper",
                       "run_user","run_baike","run_news","run_tutorial","run_custom","run_weibo"]
  - FILE user.py [size_class: large, lines: 177]
    - CLASSES: ["UserScraper(BaseScraper)"]
    - RUN_ENTRY: run(incremental:bool=False) -> Optional[str]
    - DECORATORS_ON_RUN: ["@handle_errors", "@retry(max_attempts=config retry_settings.max_attempts, delay=config retry_settings.delay)"]
    - API_KEYWORDS: ["userPostList", "postList"]
    - DOMAIN_FILTER: "miyoushe.com"
    - URL_SELECTOR_TEMPLATE: "a[href*='/ys/article/']"
  - FILE baike.py [size_class: small, lines: 38]
    - CLASSES: ["BaikeScraper(BaseScraper)"]
    - RUN_ENTRY: run() -> Optional[str]
    - DECORATORS_ON_RUN: ["@handle_errors", "@retry(3,2.0)"]
  - FILE news.py [size_class: large, lines: 203]
    - CLASSES: ["NewsScraper(BaseScraper)"]
    - RUN_ENTRY: run(incremental:bool=False) -> Optional[str]
    - DECORATORS_ON_RUN: ["@handle_errors", "@retry(3,2.0)"]
    - HARDCODED_URL: "https://ys.mihoyo.com/main/news"
    - API_KEYWORDS: ["newsList", "getNewsList", "news", "getList", "postList"]
    - DOMAIN_FILTER: "miyoushe.com"
    - URL_SELECTOR_TEMPLATE: "a[href*='/main/news/detail/']"
  - FILE weibo.py [size_class: xlarge, lines: 395]
    - CLASSES: ["WeiboScraper(BaseScraper)"]
    - RUN_ENTRY: run(incremental:bool=False) -> Optional[str]
    - DECORATORS_ON_RUN: ["@handle_errors", "@retry(3,2.0)"]
    - FORCED_HEADLESS_FALSE: true
    - USER_ID_REGEX: r'/u/(\d+)'
    - DEFAULT_USER_ID_FALLBACK: "6593199887"
    - API_KEYWORDS: ["mymblog", "statuses"]
    - DOMAIN_FILTER: "weibo.com"
    - URL_SELECTOR_TEMPLATE: "a[href*='/{user_id}/']"
    - API_PAGINATION: {
        "endpoint_template": "https://weibo.com/ajax/statuses/mymblog?uid={uid}&page={current_page}&feature=0",
        "required_headers": ["Accept", "Referer", "X-Requested-With"],
        "optional_header_xsrf": "X-XSRF-TOKEN",
        "max_pages": 500,
        "data_path": "result.data.list",
        "post_key_field": "bid",
        "post_url_template": "https://weibo.com/{uid}/{bid}"
      }
    - LOGIN_WAIT_SETTINGS: {
        "selector_for_detection": ".wbpro-scroller-item",
        "max_wait_seconds": 180,
        "poll_interval_seconds": 2
      }
  - FILE tutorial.py [size_class: small, lines: 49]
    - CLASSES: ["TutorialScraper(BaseScraper)"]
    - RUN_ENTRY: run(tutorial_id:str=None) -> Optional[str]
    - DECORATORS_ON_RUN: ["@handle_errors", "@retry(3,2.0)"]
    - DEFAULT_TUTORIAL_ID: "mh4imrrhzdzi"
    - URL_TEMPLATE: "https://act.mihoyo.com/ys/ugc/tutorial/detail/{tutorial_id}"
    - OUTPUT_FILENAME_TEMPLATE: "tutorial_{tutorial_id}.html"
  - FILE custom.py [size_class: small, lines: 70]
    - CLASSES: ["CustomScraper(BaseScraper)"]
    - RUN_ENTRY: run(url:str=None, output_filename:str="custom_page.html") -> Optional[str]
    - DECORATORS_ON_RUN: ["@handle_errors", "@retry(3,2.0)"]
    - OVERRIDES_BASE_RUN: true
    - CLI_ARGV_BINDING: {sys.argv[1]: "url", sys.argv[2]: "output_filename default custom_page.html"}
- DIR extractors/
  - FILE __init__.py [size_class: small]
    - PUBLIC_EXPORTS: ["NewsExtractor","TutorialExtractor","ImageExtractor","PostExtractor","WeiboExtractor",
                       "run_extract_news","run_extract_tutorial","run_extract_images","run_extract_time","run_extract_weibo"]
  - FILE time.py [size_class: large, lines: 177]
    - DATACLASS: PostData(date:str, title:str, url:str, index:int=0)
      - HASH_FIELDS: ("date","title","url")
    - CLASS: PostExtractor
      - INSTANCE_ATTRIBUTES:
        - html_path = output_dir.html + / + filenames.user_html
        - output_dir = output_dir.data
        - output_path = output_dir.data + / + filenames.posts_data
      - METHODS:
        - load_existing_data() -> List[PostData]
          - REGEX_LINE_PATTERN: r'\d{4}-(.+?)-\[(\d{4}-\d{2}-\d{2})\]\((https://.+?)\)'
          - REGEX_GROUPS: (title, date, url)
        - get_existing_urls() -> Set[str]
        - extract_posts(html_content:str=None, incremental:bool=False) -> List[PostData]
          - HTML_REGEX_CARD: r'<div class="mhy-account-center-post-card">([\s\S]*?)</div>\s*</div>'
          - SUB_REGEX_TIME: r'class="mhy-account-center-time__small">([^<]+)<'
          - SUB_REGEX_URL: r'href="(/ys/article/\d+)"'
          - SUB_REGEX_TITLE: r'class="mhy-article-card__h3"[^>]*>([\s\S]*?)</h3>'
          - DATE_SPLIT_CHAR: " · "
          - URL_BASE: "https://www.miyoushe.com"
          - SORT_KEY: date DESC
          - UNIQUE_BY: set(__hash__)
        - _merge_data(old:List[PostData], new:List[PostData]) -> List[PostData]
          - UNIQUE_KEY: item.url (new overwrites old)
        - _parse_date(time_str:str, now:datetime, current_year:int) -> str
          - BRANCH_hours_ago: r'(\d+)小时前' -> now - timedelta(hours=h)
          - BRANCH_mm_dd: r'\d{2}-\d{2}' -> f"{current_year}-{time_str}"
          - BRANCH_default: return as-is
        - save_post_data(post_data:List[PostData]) -> bool
          - PRE_SAVE_BACKUP_CALL: backup_manager.create_backup(output_path)
          - LINE_FORMAT: f"{index:04d}-{title}-[{date}]({url})"
          - LINE_SEPARATOR: "\n\n"
    - RUN_ENTRY: run(incremental:bool=False)
      - DECORATORS: ["@handle_errors"]
  - FILE news.py [size_class: large, lines: 186]
    - DATACLASS: NewsData(title:str, url:str, date:str, index:int=0)
      - HASH_FIELDS: ("title","url","date")
    - CLASS: NewsExtractor
      - INSTANCE_ATTRIBUTES:
        - html_path = output_dir.html + /news_page.html
        - output_dir = output_dir.data
        - output_path = output_dir.data + /news.txt
      - METHODS:
        - load_existing_data() -> List[NewsData]
          - REGEX_LINE_PATTERN: r'\d{4}-(.+?)-\[(.+?)\]-\((https://.+?)\)'
          - REGEX_GROUPS: (title, date, url)
        - get_existing_urls() -> Set[str]
        - extract_news(html_content:str=None, incremental:bool=False) -> List[NewsData]
          - STRICT_MODE_REGEX: r'<li class="news__item[^"]*">\s*<a href="(/main/news/detail/\d+)"[^>]*class="news__title[^"]*"[^>]*>.*?<h3[^>]*title="([^"]*)"[^>]*>([^<]+)</h3>.*?<div class="news__date">([^<]+)</div>'
          - STRICT_MODE_GROUPS: (url_path, title_attr, title_text, date)
          - STRICT_FALLBACK_IF_NONE: true
          - LOOSE_MODE_REGEX: r'<li class="news__item[^"]*">.*?<a href="(/main/news/detail/\d+)"[^>]*class="news__title[^"]*"[^>]*>.*?<h3[^>]*>([^<]+)</h3>.*?<div class="news__date">([^<]+)</div>'
          - LOOSE_MODE_GROUPS: (url_path, title_text, date)
          - URL_BASE: "https://ys.mihoyo.com"
          - TITLE_PRIORITY: title_attr > title_text
          - DEDUP_IN_PASS: tuple(title,url,date) in seen
          - SORT_KEY: date DESC
          - UNIQUE_BY: set(__hash__)
        - _merge_data(old:List[NewsData], new:List[NewsData]) -> List[NewsData]
          - UNIQUE_KEY: item.url (new overwrites old)
        - save_news_data(news_data:List[NewsData]) -> bool
          - PRE_SAVE_BACKUP_CALL: backup_manager.create_backup(output_path)
          - LINE_FORMAT: f"{index:04d}-{title}-[{date}]-({url})"
          - LINE_SEPARATOR: "\n"
    - RUN_ENTRY: run(incremental:bool=False)
      - DECORATORS: ["@handle_errors"]
  - FILE weibo.py [size_class: large, lines: 214]
    - DATACLASS: WeiboData(date:str, content:str, url:str, index:int=0)
      - HASH_FIELDS: ("date","content","url")
    - CLASS: WeiboExtractor
      - INSTANCE_ATTRIBUTES:
        - html_path = output_dir.html + / + filenames.weibo_html
        - output_dir = output_dir.data
        - output_path = output_dir.data + / + filenames.weibo_data
      - METHODS:
        - load_existing_data() -> List[WeiboData]
          - REGEX_LINE_PATTERN: r'\d{4}-(.+?)-\[(\d{4}-\d{2}-\d{2})\]\((https://.+?)\)'
          - REGEX_GROUPS: (content, date, url)
        - get_existing_urls() -> Set[str]
        - extract_weibo(html_content:str=None, incremental:bool=False) -> List[WeiboData]
          - PRIMARY_REGEX: r'<a class="_time_[^"]*"\s+title="([^"]+)"\s+href="(https://weibo\.com/\d+/[A-Za-z0-9]+)"'
          - SECONDARY_REGEX_IF_EMPTY: r'href="(https://weibo\.com/\d+/[A-Za-z0-9]+)"[^>]*>\s*([^<]*(?:今天|昨天|前天|\d+月\d+日|\d{4}-\d{2}-\d{2})[^<]*)'
          - CONTENT_EXTRACT: for each match, search html_content[match.end():match.end()+5000]
              with r'<div class="_wbtext_[^"]*">(.*?)</div>' -> strip tags, html.unescape, collapse whitespace
          - DEDUP_BY: url (seen_urls set)
          - SORT_KEY: date DESC
          - MERGE_INCREMENTAL: _merge_data() if incremental and merge_data config true
        - _merge_data(old,new) -> List[WeiboData]
          - UNIQUE_KEY: item.url (new overwrites old)
        - _parse_date(time_str:str) -> str
          - BRANCH_exact_yyyy_mm_dd: r'(\d{4}-\d{2}-\d{2})' -> group 1
          - BRANCH_mins_ago: r'(\d+)分钟前' -> now - timedelta(minutes=m)
          - BRANCH_hours_ago: r'(\d+)小时前' -> now - timedelta(hours=h)
          - BRANCH_yesterday: 昨天 -> now - 1d
          - BRANCH_day_before: 前天 -> now - 2d
          - BRANCH_mm_dd: r'\d{2}-\d{2}' -> current_year-
          - BRANCH_default: as-is
        - save_weibo_data(weibo_data:List[WeiboData]) -> bool
          - PRE_SAVE_BACKUP_CALL: backup_manager.create_backup(output_path)
          - LINE_FORMAT: f"{index:04d}-{content}-[{date}]({url})"
          - LINE_SEPARATOR: "\n\n"
    - RUN_ENTRY: run(incremental:bool=False)
      - DECORATORS: ["@handle_errors"]
  - FILE images.py [size_class: medium, lines: 94]
    - DATACLASS: ImageData(name:str, url:str, index:int=0)
    - CLASS: ImageExtractor
      - INSTANCE_ATTRIBUTES:
        - html_path = output_dir.html + / + filenames.baike_html
        - output_dir = output_dir.images
        - output_path = output_dir.images + / + filenames.image_urls
      - METHODS:
        - extract_image_urls(html_content:str=None) -> List[ImageData]
          - REGEX: r'class="collection-avatar__item".*?data-src="(https://.*?mihoyo\.com/.*?\.\w+)\?.*?".*?class="collection-avatar__title">(.*?)</div>'
          - REGEX_GROUPS: (img_url, name)
          - POSTPROCESS_ORDER: reversed()
          - INDEX_ASSIGN: enumerate(items, 1)
        - save_image_data(image_data:List[ImageData]) -> bool
          - LINE_FORMAT: f"{index:04d}-{name}-[{url}]"
          - LINE_SEPARATOR: "\n"
    - RUN_ENTRY: run()
      - DECORATORS: ["@handle_errors"]
  - FILE tutorial.py [size_class: medium, lines: 138]
    - DATACLASS: CharacterData(id:str, name:str, index:int=0)
      - HASH_FIELDS: ("id","name")
    - CLASS: TutorialExtractor(tutorial_id:str=None)
      - DEFAULT_TUTORIAL_ID: "mh4imrrhzdzi"
      - INSTANCE_ATTRIBUTES:
        - html_path = output_dir.html + /tutorial_{tutorial_id}.html
        - output_dir = output_dir.data
        - output_path = output_dir.data + /characters_{tutorial_id}.txt
        - tutorial_id: str
      - METHODS:
        - extract_characters(html_content:str=None) -> List[CharacterData]
          - STRICT_REGEX: r'<tr class="table-row">.*?<td[^>]*>.*?<p[^>]*>(\d+)</p>.*?<td[^>]*>.*?<p[^>]*>([^<]+)</p>.*?</tr>'
          - STRICT_FILTER_SKIP: ("对应编号", "角色名") header row
          - LOOSE_REGEX_IF_EMPTY: r'<td[^>]*>.*?<p[^>]*>(\d{7,})</p>.*?<td[^>]*>.*?<p[^>]*>([^<]+)</p>'
          - LOOSE_ID_LENGTH_GATE: len(char_id) >= 7
          - SORT_KEY: int(id) ASC
          - UNIQUE_BY: set(__hash__)
        - save_character_data(character_data:List[CharacterData]) -> bool
          - LINE_FORMAT: f"{index:04d}-{id}-{name}"
          - LINE_SEPARATOR: "\n"
    - RUN_ENTRY: run(tutorial_id:str=None)
      - DECORATORS: ["@handle_errors"]
      - CLI_ARGV_BINDING: sys.argv[1] -> tutorial_id
- DIR utils/
  - FILE __init__.py [size_class: small]
    - PUBLIC_EXPORTS: ["handle_errors","retry","ErrorHandler","setup_logger","get_module_logger",
                       "log_function_call","log_execution_time","load_firefox_cookies",
                       "find_har_file","print_har_instructions"]
  - FILE logger.py [size_class: medium, lines: 93]
    - DATACLASS: LoggerConfig(log_level:str="INFO", log_file:str="app.log",
                              max_bytes:int=10*1024*1024, backup_count:int=5)
    - FUNCTION setup_logger(name:str, config:Optional[LoggerConfig]=None) -> logging.Logger
      - HANDLERS: [FileHandler(logs/app.log, utf-8), StreamHandler(sys.stdout)]
      - FORMAT: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      - DATEFMT: '%Y-%m-%d %H:%M:%S'
      - REENTRANT_SAFE: returns existing if logger.handlers non-empty
    - FUNCTION get_module_logger(module_name:str) -> logging.Logger
    - DECORATOR log_function_call(func)
      - ENTER_LOG: "调用函数: {func.__name__}" level=INFO
      - EXIT_NORMAL_LOG: "函数 {func.__name__} 执行成功"
      - EXIT_EXCEPTION_LOG: "函数 {func.__name__} 执行失败: {e}" + exc_info
      - RETHROW_ON_EXCEPTION: true
    - DECORATOR log_execution_time(func)
      - ENTER: time.time()
      - EXIT_NORMAL: log execution_time:.2f秒
      - EXIT_EXCEPTION: log error + execution_time
  - FILE error_handler.py [size_class: medium, lines: 86]
    - DECORATOR handle_errors(func) -> Callable
      - EXCEPTION_CLASSES_CAUGHT: [FileNotFoundError, ConnectionError, TimeoutError, Exception]
      - RETURN_ON_EXCEPTION: None
      - PRINT_FORMAT: "❌ 错误：{friendly_label} - {e}"
    - DECORATOR retry(max_attempts:int=3, delay:float=2.0, exceptions:Tuple[Type[Exception],...]=(Exception,))
      - LOOP: for attempt in range(max_attempts)
      - FAIL_ACTION_BETWEEN: time.sleep(delay) + print(f"⚠️ 第{attempt+1}次尝试失败...")
      - FINAL_FAILURE: raise last_exception after max_attempts exhausted
    - CLASS ErrorHandler (static class)
      - METHOD safe_execute(func, *args, default_return=None, **kwargs) -> Any
      - METHOD validate_file_exists(filepath:str) -> bool
          - ACTION_IF_MISSING: log ERROR + print ❌ + return False
      - METHOD validate_directory_exists(dirpath:str) -> bool
          - ACTION_IF_MISSING: os.makedirs(exist_ok=True) + print 📁 + return True on success else False
  - FILE backup_manager.py [size_class: xlarge, lines: 214]
    - DATACLASS: BackupInfo(filename:str, filepath:str, created_at:datetime, size:int)
    - CLASS BackupManager(backup_dir:str="data/backups", max_backups:int=10)
      - DEFAULT_CONSTRUCTOR_BACKUP_DIR: "data/backups"
      - DEFAULT_CONSTRUCTOR_MAX_BACKUPS: 10
      - GLOBAL_SINGLETON: backup_manager = BackupManager()
      - METHOD _ensure_backup_dir() -> None: Path(backup_dir).mkdir(parents=True, exist_ok=True)
      - METHOD _get_backup_subdir(filename:str) -> str: backup_dir + / + Path(filename).stem
      - METHOD create_backup(source_file:str, backup_name:Optional[str]=None) -> Optional[str]
          - FILENAME_FORMAT: {stem}_{YYYYMMDD_HHMMSS}{ext}
          - COPY_STRATEGY: shutil.copy2
          - POST_COPY_ACTION: _cleanup_old_backups()
      - METHOD _cleanup_old_backups(backup_subdir:str, base_name:str) -> None
          - SORT_KEY: st_mtime DESC
          - REMOVE_IF_INDEX >= max_backups: os.remove()
      - METHOD list_backups(filename:str) -> List[BackupInfo]
          - SORT_KEY: created_at DESC
      - METHOD restore_backup(backup_path:str, target_path:str) -> bool
          - PRE_COPY_TEMP_BACKUP_IF_EXISTS: target_path -> {target_path}.before_restore_{YYYYMMDD_HHMMSS}
          - COPY: shutil.copy2(backup_path, target_path)
      - METHOD get_latest_backup(filename:str) -> Optional[str]
      - METHOD get_backup_size_mb(filename:str) -> float
  - FILE cookie_loader.py [size_class: large, lines: 118]
    - FUNCTION find_firefox_profile() -> Optional[str]
      - ENV_VAR: %APPDATA% (Windows-only)
      - BASE_DIR: %APPDATA%/Mozilla/Firefox/Profiles
      - PREFERRED_DIR_NAME_KEYWORDS: ["default-release", "default"]
      - FILE_PROBE: entry_path + /cookies.sqlite exists
      - FALLBACK: any subdir with cookies.sqlite
    - FUNCTION load_firefox_cookies(domain_filter:str=None) -> List[Dict[str,str]]
      - STRATEGY: copy cookies.sqlite to tempfile/sqlite_read/delete temp
      - TABLE_QUERIED: moz_cookies
      - COLUMNS: name, value, host, path, expiry, isSecure, isHttpOnly, sameSite
      - WHERE_IF_FILTER: host LIKE ? %domain_filter%
      - SAMESITE_MAP: {0:"None", 1:"Lax", 2:"Strict"}
      - EXPIRY_NORMALIZE: if expiry > 1e12 divide by 1000; if None/<=0 return -1
      - OUTPUT_FORMAT_PLAYWRIGHT_COOKIE: {name,value,domain=host,path,expires,secure=bool(isSecure),httpOnly=bool(isHttpOnly),sameSite}
  - FILE har_loader.py [size_class: large, lines: 167]
    - CONSTANT HAR_BASE_DIR: project_root + /har
    - FUNCTION get_har_dir(scraper_name:str) -> str
    - FUNCTION find_har_file(scraper_name:str) -> Optional[str]
        - EXTENSIONS: ['.har', '.txt'] case-insensitive
    - FUNCTION parse_har_file(har_path:str) -> List[dict]
        - FEATURE: supports concatenated multiple JSON objects in single file via JSONDecoder.raw_decode loop
        - OUTPUT: flat list of all entries from obj['log']['entries']
    - FUNCTION extract_api_patterns(har_path:str, domain_keywords:List[str]=None) -> List[dict]
        - METHOD_FILTER: only GET requests
        - DOMAIN_FILTER: any(kw in url for kw in domain_keywords) if provided
        - MIME_FILTER: 'json' in mimeType or has text content
        - DEDUP_BY_SEEN_URLS: set()
        - OUTPUT_ITEMS: {url, method, params(queryString name->value), headers(lowercase name->value), has_json_response, status}
    - FUNCTION print_har_instructions(scraper_name:str, page_url:str, domain_keywords:List[str]=None)
        - SIDE_EFFECT: os.makedirs(har_dir, exist_ok=True)
        - STEPS: 9-step F12 Firefox Network Persist Logs Scroll Save All As HAR copy to get_har_dir
    - FUNCTION load_api_pattern_from_har(scraper_name:str, domain_keywords:List[str]=None) -> Optional[dict]
        - OUTPUT: {url_pattern=path_split_last, full_url_template, domain, params, FILTERED_HEADERS:[ds, x-rpc-app_version, x-rpc-client_type, x-rpc-device_fp, x-rpc-device_id, referer, origin]}
- DIR tests/
  - FILE __init__.py: empty
  - FILE test_extractors.py [size_class: medium, lines: 122]
    - FRAMEWORK: unittest
    - EXEC_COMMAND: python -m unittest tests.test_extractors -v
    - CLASSES: [TestImageExtractor, TestPostExtractor, TestConfigManager]
    - TEST_CASE_COUNT: 6
    - CASES:
      - TestImageExtractor.test_extract_image_urls: asserts len==2, reversed order
      - TestImageExtractor.test_save_image_data: uses tempfile.TemporaryDirectory, validates output text
      - TestPostExtractor.test_extract_posts: asserts title/date/url fields
      - TestPostExtractor.test_parse_date: three branches with fixed datetime(2024,1,20,12,0,0)
      - TestConfigManager.test_config_loading: writes custom json to temp dir, asserts get()
- FILE main.py [size_class: xlarge, lines: 645]
  - IMPORTS: [sys, os, platform, typing:Dict,Optional,
              core.config_manager:config_manager,
              utils.error_handler:handle_errors,
              utils.logger:setup_logger,log_function_call,
              utils.backup_manager:backup_manager]
  - LOGGER_NAME: "miHoYo_ToolKit"
  - CLASS MiHoYoToolKit
    - ATTRIBUTES: version="2.1.0", title=computed f-string, options=Dict from _setup_options()
    - METHOD _setup_options() -> Dict[str, Dict[label, description, handler]]
        - KEYS: ["1".."23"] exactly 23 entries; menu also prints "0. 退出程序"
    - METHOD _clear_screen() -> None: os.system('cls' if nt else 'clear')
    - METHOD _print_header() -> None: 70-char = banner
    - METHOD _print_menu() -> None: sorted keys by int
    - ALL HANDLERS APPLY_DECORATORS: ["@log_function_call", "@handle_errors"]
    - HANDLERS_LAZY_IMPORTS: each handler does `from fetchers import X` / `from extractors import X` at top of body
      - {1:"_fetch_user_posts"           -> fetchers.run_user(incremental=False)}
      - {2:"_incremental_fetch_user_posts" -> fetchers.run_user(incremental=True)}
      - {3:"_fetch_character_baike"      -> fetchers.run_baike()}
      - {4:"_fetch_genshin_news"         -> fetchers.run_news(incremental=False)}
      - {5:"_incremental_fetch_news"     -> fetchers.run_news(incremental=True)}
      - {6:"_fetch_tutorial_page"        -> fetchers.run_tutorial(input_id or "mh4imrrhzdzi")}
      - {7:"_extract_tutorial_data"      -> extractors.run_extract_tutorial(input_id or "mh4imrrhzdzi")}
      - {8:"_fetch_custom_site"          -> fetchers.run_custom(input_url, input_filename or "custom_page.html")}
      - {9:"_extract_image_urls"         -> extractors.run_extract_images()}
      - {10:"_extract_post_times"        -> extractors.run_extract_time(incremental=False)}
      - {11:"_incremental_extract_posts" -> extractors.run_extract_time(incremental=True)}
      - {12:"_extract_news_data"         -> extractors.run_extract_news(incremental=False)}
      - {13:"_incremental_extract_news"  -> extractors.run_extract_news(incremental=True)}
      - {14:"_fetch_weibo_posts"         -> fetchers.run_weibo(incremental=False)}
      - {15:"_incremental_fetch_weibo_posts" -> fetchers.run_weibo(incremental=True)}
      - {16:"_extract_weibo_data"        -> extractors.run_extract_weibo(incremental=False)}
      - {17:"_incremental_extract_weibo_data" -> extractors.run_extract_weibo(incremental=True)}
      - {18:"_show_backups"              -> print posts+news+weibo backups via backup_manager.list_backups}
      - {19:"_restore_backup"            -> submenu 1/2/3 -> _restore_{posts,news,weibo}_backup via backup_manager.restore_backup}
      - {20:"_show_config"               -> print config_manager.get(key) for each key}
      - {21:"_modify_config"             -> prompt user_url/baike_url/weibo_url/wait_seconds then config_manager.save_config()}
      - {22:"_reload_config"             -> config_manager.load_config()}
      - {23:"_show_system_info"          -> print platform, python version, cwd, playwright version if installed}
    - METHOD run() -> None: infinite while True loop, input choice, if "0" sys.exit(0), else invoke handler with try/except KeyboardInterrupt and Exception
  - FUNCTION main() -> None:
    - DECORATORS: ["@handle_errors"]
    - PREFLIGHT_CHECK: try import playwright, fail with install instructions if ImportError
    - ACTION: instantiate MiHoYoToolKit then call .run()

================================================================================
SECTION_02: CONFIG_SCHEMA
================================================================================
CONFIG_FILE: config.json
FORMAT: JSON
TOP_LEVEL_KEYS_COUNT: 15
SCHEMA:
{
  "user_url": {"type":"string","default":"https://www.miyoushe.com/ys/accountCenter/postList?id=75276539","used_by":["fetchers.user:功能1,2"]},
  "baike_url": {"type":"string","default":"https://baike.mihoyo.com/ys/obc/channel/map/189/25","used_by":["fetchers.baike:功能3"]},
  "weibo_url": {"type":"string","default":"https://weibo.com/u/6593199887","used_by":["fetchers.weibo:功能14,15"]},
  "headless": {"type":"boolean","default":false,"used_by":["core.scraper.BaseScraper._setup_browser"]},
  "wait_seconds": {"type":"integer","default":3,"used_by":["core.scraper.BaseScraper._process_page after networkidle"]},
  "timeout": {"type":"integer","default":120000,"used_by":["page.goto timeout ms"]},
  "user_agent": {"type":"string","default":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36","used_by":["BrowserContext user_agent"]},
  "output_dirs": {
    "type":"object",
    "keys": {
      "html": {"type":"string","default":"data/html"},
      "images": {"type":"string","default":"data/images"},
      "data": {"type":"string","default":"data/results"}
    }
  },
  "filenames": {
    "type":"object",
    "keys": {
      "user_html": {"type":"string","default":"user_posts.html"},
      "baike_html": {"type":"string","default":"character_list.html"},
      "image_urls": {"type":"string","default":"image_urls.txt"},
      "posts_data": {"type":"string","default":"posts.txt"},
      "weibo_html": {"type":"string","default":"weibo_posts.html","source":"Filenames dataclass"},
      "weibo_data": {"type":"string","default":"weibo.txt","source":"Filenames dataclass"}
    }
  },
  "browser_args": {"type":"array[string]","default":["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"]},
  "scroll_settings": {
    "type":"object",
    "keys": {
      "delay": {"type":"number","default":2.0,"used_by":["BaseScraper scroll sleep"]},
      "max_scroll_attempts": {"type":"integer","default":50,"used_by":["UNUSED - hardcoded 3/5 attempts in scroll functions"]}
    }
  },
  "retry_settings": {
    "type":"object",
    "keys": {
      "max_attempts": {"type":"integer","default":3},
      "delay": {"type":"number","default":2.0}
    }
  },
  "incremental_settings": {
    "type":"object",
    "keys": {
      "enabled": {"type":"boolean","default":true},
      "stop_on_existing": {"type":"boolean","default":true},
      "merge_data": {"type":"boolean","default":true}
    }
  },
  "backup_settings": {
    "type":"object",
    "keys": {
      "enabled": {"type":"boolean","default":true},
      "max_backups": {"type":"integer","default":10},
      "backup_dir": {"type":"string","default":"data/backups"}
    }
  },
  "weibo_settings": {
    "type":"object",
    "keys": {
      "use_firefox_cookies": {"type":"boolean","default":true,"used_by":["fetchers.weibo WeiboScraper __init__"]}
    }
  },
  "miyoushe_settings": {
    "type":"object",
    "keys": {
      "use_firefox_cookies": {"type":"boolean","default":true,"used_by":["fetchers.user, fetchers.news __init__"]}
    }
  }
}
CONFIG_MANAGER_METHODS:
- ConfigManager(config_file:str="config.json")
  - INSTANCE_VARS: [config_file:str, base_dir:str (parent of dirname(__file__)), config_path:str (join(base_dir,config_file)), default_config:Dict, config:Dict]
  - LOAD_ORDER: default_config deep_updated by user file if exists
- get(key:str, default=None) -> Any: supports dot-notation nested path (split by '.')
- set(key:str, value:Any) -> None: supports dot-notation, auto-creates intermediate dicts
- load_config() -> None: reads json from disk, on error WARN + keep defaults
- save_config() -> None: writes json with ensure_ascii=False indent=2
- get_output_dir(dir_type:str) -> str: joins base_dir + config.output_dirs[dir_type] + makedirs(exist_ok=True)
- get_filename(file_type:str) -> str: returns config.filenames[file_type] or ""
- get_scraper_config(url:str, output_filename:str) -> Dict[str,Any]: builds ScraperConfig kwargs dict

================================================================================
SECTION_03: MENU_FUNCTIONS_COMPLETE_BINDING
================================================================================
MENU_PROMPT: "请输入序号："
EXIT_KEY: "0"

[1] LABEL:抓取用户发帖主页            CLASS:UserScraper    FETCHER:run_user    INCREMENTAL:false  EXTRACTOR:N/A          OUTPUT:data/html/user_posts.html
[2] LABEL:增量抓取用户发帖            CLASS:UserScraper    FETCHER:run_user    INCREMENTAL:true   EXTRACTOR:N/A          OUTPUT:data/html/user_posts.html    STOP_ON_EXISTING:true
[3] LABEL:抓取角色图鉴页面            CLASS:BaikeScraper   FETCHER:run_baike   INCREMENTAL:false  EXTRACTOR:N/A          OUTPUT:data/html/character_list.html
[4] LABEL:抓取原神新闻页面            CLASS:NewsScraper    FETCHER:run_news    INCREMENTAL:false  EXTRACTOR:N/A          OUTPUT:data/html/news_page.html     URL:HARDCODED_ys.mihoyo.com/main/news
[5] LABEL:增量抓取原神新闻            CLASS:NewsScraper    FETCHER:run_news    INCREMENTAL:true   EXTRACTOR:N/A          OUTPUT:data/html/news_page.html     STOP_ON_EXISTING:true
[6] LABEL:抓取米游社教程页面          CLASS:TutorialScraper FETCHER:run_tutorial INCREMENTAL:false  EXTRACTOR:N/A          OUTPUT:data/html/tutorial_{tid}.html  INPUT_PROMPT:"教程ID [mh4imrrhzdzi]: "
[7] LABEL:提取教程角色数据            CLASS:N/A            FETCHER:N/A         INCREMENTAL:N/A    EXTRACTOR:TutorialExtractor OUTPUT:data/results/characters_{tid}.txt  INPUT_PROMPT:"教程ID [mh4imrrhzdzi]: "
[8] LABEL:抓取自定义网站              CLASS:CustomScraper  FETCHER:run_custom  INCREMENTAL:false  EXTRACTOR:N/A          OUTPUT:data/html/{filename}             INPUT_PROMPT_URL:"请输入要抓取的网站URL: "   INPUT_PROMPT_FILENAME:"请输入输出文件名 [custom_page.html]: "
[9] LABEL:提取图鉴图片链接            CLASS:N/A            FETCHER:N/A         INCREMENTAL:N/A    EXTRACTOR:ImageExtractor    OUTPUT:data/images/image_urls.txt
[10] LABEL:提取用户发帖时间           CLASS:N/A            FETCHER:N/A         INCREMENTAL:false  EXTRACTOR:PostExtractor     OUTPUT:data/results/posts.txt
[11] LABEL:增量提取用户发帖           CLASS:N/A            FETCHER:N/A         INCREMENTAL:true   EXTRACTOR:PostExtractor     OUTPUT:data/results/posts.txt    MERGE:true
[12] LABEL:提取原神新闻数据           CLASS:N/A            FETCHER:N/A         INCREMENTAL:false  EXTRACTOR:NewsExtractor     OUTPUT:data/results/news.txt
[13] LABEL:增量提取新闻数据           CLASS:N/A            FETCHER:N/A         INCREMENTAL:true   EXTRACTOR:NewsExtractor     OUTPUT:data/results/news.txt     MERGE:true
[14] LABEL:抓取微博用户主页           CLASS:WeiboScraper   FETCHER:run_weibo   INCREMENTAL:false  EXTRACTOR:N/A               OUTPUT:data/html/weibo_posts.html  FORCED_HEADLESS_FALSE:true
[15] LABEL:增量抓取微博用户           CLASS:WeiboScraper   FETCHER:run_weibo   INCREMENTAL:true   EXTRACTOR:N/A               OUTPUT:data/html/weibo_posts.html  STOP_ON_EXISTING:true  FORCED_HEADLESS_FALSE:true
[16] LABEL:提取微博数据               CLASS:N/A            FETCHER:N/A         INCREMENTAL:false  EXTRACTOR:WeiboExtractor    OUTPUT:data/results/weibo.txt
[17] LABEL:增量提取微博数据           CLASS:N/A            FETCHER:N/A         INCREMENTAL:true   EXTRACTOR:WeiboExtractor    OUTPUT:data/results/weibo.txt     MERGE:true
[18] LABEL:查看备份文件               CLASS:N/A            FETCHER:N/A         ACTION:backup_manager.list_backups("posts.txt" then "news.txt" then "weibo.txt")  DISPLAYS:filename+created_at+size_kb+filepath
[19] LABEL:恢复备份数据               CLASS:N/A            FETCHER:N/A         ACTION:sub_menu(1:posts 2:news 3:weibo 0:return) -> list -> select index -> backup_manager.restore_backup()
[20] LABEL:查看当前配置               CLASS:N/A            FETCHER:N/A         ACTION:print config_manager.get() for keys:[user_url,baike_url,weibo_url,headless,wait_seconds,timeout,retry_settings.max_attempts,incremental_settings.enabled,backup_settings.enabled,backup_settings.max_backups,config_path]
[21] LABEL:修改配置参数               CLASS:N/A            FETCHER:N/A         ACTION:prompt each (empty=keep) user_url,baike_url,weibo_url,wait_seconds(isdigit gate) -> config_manager.set() -> save_config()
[22] LABEL:重新加载配置               CLASS:N/A            FETCHER:N/A         ACTION:config_manager.load_config()
[23] LABEL:系统信息                   CLASS:N/A            FETCHER:N/A         ACTION:print platform.system()+release(), python_version, __file__ dir, config_path, playwright version (from _repo_version.version)
[0]  LABEL:退出程序                   CLASS:N/A            ACTION:sys.exit(0)

================================================================================
SECTION_04: BASESCRAPER_INTERFACE
================================================================================
CLASS BaseScraper(config:ScraperConfig)
  ATTRIBUTES:
    config: ScraperConfig
    html_dir: str (from config_manager.get_output_dir("html"))
    save_path: str (join(html_dir, config.output_filename))
    url_selector_template: str (default: "a[href*='/article/'], a[href*='/news/']")
    _api_data: List[Dict]
    _api_stop_requested: bool
  METHODS:
    _setup_browser(playwright) -> tuple[Browser,Page]
      - chromium.launch(headless=headless, args=browser_args + (["--start-maximized"] if not headless))
      - new_context(user_agent=user_agent, no_viewport=True)
      - if use_firefox_cookies and api_domain_filter: context.add_cookies(load_firefox_cookies(domain_filter=api_domain_filter))
      - return (browser, context.new_page())
    _setup_api_interception(page:Page, on_data_callback:Callable=None) -> None
      - register page.on('response', handle_response)
      - handle_response: if response.ok and any(kw in url) and response.json() parseable -> extract items via callback or _extract_items_from_api -> extend _api_data -> if incremental and stop_on_existing and any item.url in existing_urls -> _api_stop_requested=True
    _extract_items_from_api(data:dict) -> list: default empty, overridden by User/News/Weibo
    _build_html_from_api_data(items:list) -> str: default empty, overridden by User/News/Weibo
    _check_api_data_or_har() -> Optional[str]: if not _api_data -> find_har_file(scraper_name) -> return "use_har" marker if found else print_har_instructions + return None
    _scroll_to_bottom(page:Page) -> None: while True scroll sleep; if 3 consecutive same height -> break; if incremental _check_existing_urls returns True + stop_on_existing -> break
    _check_existing_urls(page:Page) -> bool: page.evaluate Array.from(querySelectorAll(url_selector_template)).map(href).filter /article/ or /news/ -> any in existing_urls
    _process_page(page:Page) -> str: goto, wait_for_load_state("networkidle"), sleep wait_seconds, _scroll_to_bottom, return page.content()
    run() -> str: sync_playwright context -> setup_browser -> _process_page -> browser.close (finally) -> _save_html -> return html_content
    _save_html(html_content:str) -> None: open(save_path, "w", utf-8) write
    extract_data(html_content:str) -> Any: raises NotImplementedError (abstract)

SUBCLASS_OVERRIDE_MAP:
  UserScraper:  overrides _extract_items_from_api, _build_html_from_api_data, _process_page, _scroll_for_data (custom variant)
  NewsScraper:  overrides _extract_items_from_api, _build_html_from_api_data, _process_page, _scroll_for_data (click more button)
  WeiboScraper: overrides _process_page, _fetch_posts_via_api (direct API pagination), _build_html, _build_post_html,
                           _wait_for_login, _extract_user_id, _check_existing_urls
  BaikeScraper: no overrides (pure BaseScraper defaults)
  TutorialScraper: no overrides
  CustomScraper: overrides run() method directly (simpler flow, no API interception)

================================================================================
SECTION_05: GITIGNORE_IGNORED_PATHS
================================================================================
PATTERNS (auto-generated at runtime, not committed):
__pycache__/ *.pyc *.pyo *.pyd .Python
venv/ .env/ .env.local .venv/
data/ html_output/ image_urls/
har/*/ (note: har/ base dir itself kept; all subdirs ignored to prevent cookie leakage)
logs/
.vscode/ .idea/ *.swp *.swo *~ .DS_Store Thumbs.db
build/ dist/ *.spec
.test/ .coverage htmlcov/
# config.json line commented out - file IS tracked by default

================================================================================
SECTION_06: CORE_DATA_INTERCHANGE_FORMATS
================================================================================
FMT_posts_txt_LINE:
  REGEX: ^(\d{4})-(.+?)-\[(\d{4}-\d{2}-\d{2})\]\((https://www\.miyoushe\.com/ys/article/\d+)\)$
  GROUPS: (index_padded, title, date_yyyy_mm_dd, full_url)
  SEPARATOR_BETWEEN_LINES: \n\n (blank line between records)

FMT_news_txt_LINE:
  REGEX: ^(\d{4})-(.+?)-\[(.+?)\]-\((https://ys\.mihoyo\.com/main/news/detail/\d+)\)$
  GROUPS: (index_padded, title, date_string, full_url)
  SEPARATOR_BETWEEN_LINES: \n (single newline)

FMT_weibo_txt_LINE:
  REGEX: ^(\d{4})-(.+?)-\[(\d{4}-\d{2}-\d{2})\]\((https://weibo\.com/\d+/[A-Za-z0-9]+)\)$
  GROUPS: (index_padded, content_text_plain, date_yyyy_mm_dd, full_url)
  SEPARATOR_BETWEEN_LINES: \n\n (blank line between records)

FMT_image_urls_txt_LINE:
  REGEX: ^(\d{4})-(.+?)-\[(https://upload-bbs\.mihoyo\.com/[^]]+)\]$
  GROUPS: (index_padded, character_name, image_url_stripped_of_query_params)
  SEPARATOR_BETWEEN_LINES: \n

FMT_characters_txt_LINE:
  REGEX: ^(\d{4})-(\d{7,})-(.+)$
  GROUPS: (index_padded, character_id_numeric, character_name)
  SEPARATOR_BETWEEN_LINES: \n
  SORT_ORDER: character_id_numeric ASC

BACKUP_FILENAME_FMT: {original_stem}_YYYYMMDD_HHMMSS{original_ext}
  EXAMPLE: posts_20260821_143022.txt
  LOCATION_PER_ORIGINAL: data/backups/{original_stem}/   (e.g. data/backups/posts/posts_....txt)

================================================================================
SECTION_07: PLATFORM_COMPATIBILITY_MATRIX
================================================================================
Windows: FULL_SUPPORT
  - Firefox cookie loader: SUPPORT (uses %APPDATA%)
  - Clear screen: "cls"
  - Path separator: auto-handled by os.path
macOS: PARTIAL_SUPPORT
  - Firefox cookie loader: NOT_SUPPORT (hardcoded %APPDATA% -> prints "未找到 Firefox 配置文件" -> login by manual scan)
  - Clear screen: "clear"
Linux: PARTIAL_SUPPORT
  - Firefox cookie loader: NOT_SUPPORT
  - Clear screen: "clear"
  - Chromium sandbox: requires browser_args "--no-sandbox --disable-dev-shm-usage" (already in defaults for Docker/CI)

END_OF_DOCUMENT_V1
