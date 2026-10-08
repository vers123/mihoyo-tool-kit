# 公开 API 声明

本项目遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

SemVer 规范第 1 条要求「使用语义化版本的软件**必须声明公开 API**」。本文档即该声明：
**只有下列内容属于受版本号约束的公开接口**。未列入的模块、类、函数、字段一律视为
内部实现，可随时调整而不提升 MAJOR 版本。

当前版本：**2.1.0**

| 面 | 载体 | 破坏性变动示例 |
| ------ | ------ | ------ |
| CLI 命令与参数 | `cli/registry.py` 的命令 key 与分组、`__main__.py` 的 argparse | 删除 / 重命名命令 key、改分组归属、改参数名或取值集合 |
| Python 包 API | 各子包 `__all__` 列出的符号 | 删除 / 重命名公开符号、改函数签名 |
| 配置格式 | `config.toml` 小节与字段、`MIHOYO_*` 环境变量 | 改字段名 / 语义、改加载优先级 |
| 数据与目录约定 | `data/`、`logs/`、`har/`、`output/` 的文件名与结构 | 改数据库表 / 列、改 HTML / 导出文件名 |
| GUI 导航结构 | 由命令注册表派生的导航分组与顺序 | 删除功能入口（新增或重排不算破坏） |

---

## 1. CLI 命令与参数

### 1.1 交互命令（43 项 / 9 分组）

命令 `key` 是稳定标识，注册于 `mihoyo_toolkit/cli/registry.py`，标签与说明可改，
`key` 与分组归属属于公开 API。

| 分组 | 命令 key |
| ------ | ------ |
| 米游社用户 | `user.fetch`、`user.fetch_incremental`、`user.extract`、`user.extract_incremental` |
| 原神新闻 | `genshin.fetch`、`genshin.fetch_incremental`、`genshin.extract`、`genshin.extract_incremental` |
| 原神英文版新闻 | `genshin_en.fetch`、`genshin_en.fetch_incremental`、`genshin_en.extract`、`genshin_en.extract_incremental` |
| 绝区零新闻 | `zzz.fetch`、`zzz.fetch_incremental`、`zzz.extract`、`zzz.extract_incremental` |
| 星穹铁道新闻 | `starrail.fetch`、`starrail.fetch_incremental`、`starrail.extract`、`starrail.extract_incremental` |
| 其他抓取 | `other.baike`、`other.tutorial`、`other.tutorial_batch`、`other.extract_tutorial`、`other.images`、`other.custom`、`other.model_download` |
| 微博 | `weibo.fetch`、`weibo.fetch_incremental`、`weibo.extract`、`weibo.extract_incremental` |
| 系统工具 | `system.backups`、`system.restore`、`system.config_show`、`system.config_edit`、`system.config_reload`、`system.info`、`system.migrate`、`system.clean` |
| 数据导出 | `export.excel`、`export.rss`、`export.json`、`export.filter` |

### 1.2 非交互参数

```text
mihoyo-toolkit [--gui]
               [--fetch {genshin,genshin_en,zzz,starrail,all}]
               [--export-excel] [--export-feed {rss,json}]
               [--count] [--filter] [--migrate] [--version]
```

`mihoyo-toolkit-gui` 为 GUI 入口脚本；`python -m mihoyo_toolkit` 与根级 `run.py` 等价。

---

## 2. Python 包 API

`mihoyo_toolkit` 顶层公开 `__version__`、`__author__`、`__license__`。
各子包以下列 `__all__` 为准（函数签名与语义属于公开 API）：

| 子包 | 公开符号 |
| ------ | ------ |
| `core` | `ToolkitSettings`、`get_settings`、`reload_settings`、`PathManager`、`get_path_manager`、`Storage`、`NewsItem`、`PostItem`、`WeiboItem`、`TutorialItem`、`ImageItem`、`ChangelogEntry`、`MihoyoError`、`ConfigError`、`NetworkError`、`RetryExhausted`、`AuthError`、`ParseError`、`StorageError`、`ScraperError`、`GuiError` |
| `scrapers` | `BaseScraper`、`BrowserSession`、`open_browser`、`ScrapeConfig`、`MiHoYoApiClient`、`fetch_all_games`、`fetch_all_games_async`、`GameNewsScraper`、`get_scraper`、`run_news`、`run_all_news`、`run_news_genshin`、`run_news_genshin_en`、`run_news_zzz`、`run_news_starrail`、`UserScraper`、`run_user`、`WeiboScraper`、`run_weibo`、`BaikeScraper`、`run_baike`、`TutorialScraper`、`run_tutorial`、`run_tutorial_batch`、`CustomScraper`、`run_custom`、`run_model_download` |
| `extractors` | `ChangelogExtractor`、`GameNewsBaseExtractor`、`GenshinNewsExtractor`、`GenshinENNewsExtractor`、`ZZZNewsExtractor`、`SRNewsExtractor`、`PostExtractor`、`WeiboExtractor`、`TutorialExtractor`、`ImageExtractor`、`run_extract_news`、`run_extract_posts`、`run_extract_weibo`、`run_extract_tutorial`、`run_extract_images` |
| `exporters` | `ExcelWriter`、`FeedGenerator`、`export_news_excel`、`generate_rss_feed`、`generate_json_feed` |
| `cli` | `Command`、`CommandRegistry`、`Menu`、`registry` |
| `gui` | `MainWindow`、`launch_gui`、`NavEntry`、`build_nav` |
| `utils` | `setup_console_log`、`setup_logger`、`get_module_logger`、`append_gui_log`、`log_function_call`、`find_har_file`、`get_har_dir`、`get_har_welcome_text`、`get_har_welcome_html`、`load_har_entries`、`parse_har_file`、`print_har_instructions`、`find_firefox_profile`、`load_firefox_cookies`、`BackupInfo`、`BackupManager`、`backup_manager`、`DataMigrationManager`、`check_and_migrate`、`MatchResult`、`TxtFilter`、`run_filter` |

数据模型字段名（`NewsItem` / `PostItem` / `WeiboItem` / `TutorialItem` / `ImageItem`）属于
公开 API，其中沿用米哈游原始命名的字段（如 `iInfoId`、`sTitle`）保持原样。

---

## 3. 配置格式与环境变量

配置文件为 `config.toml`，小节：`app`、`fetch`、`retry`、`incremental`、`backup`、
`cookies`、`sources.user`、`sources.baike`、`sources.weibo`、
`sources.news.{genshin,genshin_en,zzz,starrail}`。

环境变量覆盖：前缀 `MIHOYO_`，嵌套用 `__` 分隔，例如
`MIHOYO_FETCH__HEADLESS=false`、`MIHOYO_RETRY__MAX_ATTEMPTS=5`。

| 特殊变量 | 作用 |
| ------ | ------ |
| `MIHOYO_HOME` | 覆盖项目根目录（测试与多实例隔离用） |
| `MIHOYO_DATA_DIR` | 单独覆盖数据目录 |
| `MIHOYO_LEGACY_DIR` | 指定 v1 旧数据目录，供 `--migrate` 迁移 |

加载优先级（高 → 低）：**初始化参数 > 环境变量 > `config.toml`**。

---

## 4. 数据与目录约定

| 路径 | 内容 |
| ------ | ------ |
| `data/toolkit.db` | 统一 SQLite 库，表：`news`、`posts`、`weibo`、`tutorial`、`images` |
| `data/html/{game}_news.html` | 四站点新闻 HTML（`genshin` / `genshin_en` / `zzz` / `starrail`） |
| `data/html/` 其他 | `user_posts.html`、`weibo_posts.html`、`baike_characters.html`、`tutorial_*.html` |
| `data/results/*.txt` | 提取层导出的 TXT（如 `genshin_news.txt`、`posts.txt`） |
| `data/images/`、`data/models/`、`data/backups/` | 图片链接、角色模型、自动备份 |
| `logs/console.log`、`logs/gui.log`、`logs/app.log` | 三类日志（终端镜像 / GUI 面板 / 结构化日志） |
| `har/{scraper_name}/` | HAR 回退文件目录 |
| `output/news.xlsx`、`output/news_feed.xml`、`output/news_feed.json` | 导出产物 |

`data/`、`logs/`、`har/`、`output/` 均在 `.gitignore` 中，属运行期目录。

---

## 5. GUI 导航结构

导航项由命令注册表派生（`gui/nav.py`），共 **10 项**：9 个命令分组 +
`export.filter`（TXT 过滤）单独成页；顺序与 CLI 菜单一致。

| 导航项 | 负责的命令 |
| ------ | ------ |
| 米游社用户 | `user.*` |
| 原神新闻 / 原神英文版新闻 / 绝区零新闻 / 星穹铁道新闻 | 对应 `{game}.*` |
| 其他抓取 | `other.*` |
| 微博 | `weibo.*` |
| 系统工具 | `system.*` |
| 数据导出 | `export.excel`、`export.rss`、`export.json` |
| TXT 过滤 | `export.filter` |

新增命令时若未在 `gui/nav.py` 登记页面，装配阶段会抛出 `GuiError`（有测试覆盖），
因此 GUI 不可能静默缺少入口。

---

## 6. 版本号判定（本项目承诺）

- **MAJOR**（`X.0.0`）：破坏上表任一面 —— 删除 / 重命名命令 key、改 `config.toml`
  字段名或环境变量语义、改数据库表列、改导出或 HTML 文件名、删除公开符号。
- **MINOR**（`x.Y.0`）：向后兼容地**新增** —— 新命令、新配置项、新公开符号、新数据
  字段；也包括内部架构的重大改进（SemVer 规范第 7 条「MAY」）。标记弃用时同样提升
  MINOR，并在至少一个 MINOR 版本内保留旧入口。
- **PATCH**（`x.y.Z`）：向后兼容的缺陷修复与文档、内部实现调整，不改变上述公开面。

已发布版本的内容不再修改：任何调整都以新版本号发布（规范第 3 条）。
