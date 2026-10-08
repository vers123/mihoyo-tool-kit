# 米游社工具箱 / miHoYo ToolKit

> 米游社 / 微博 / 米哈游四站点新闻数据抓取与提取工具 · CLI 与 GUI 双模式

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.1.1-green)](CHANGELOG.md)

**[快速开始](#快速开始)** ·
**[功能列表](#功能列表)** ·
**[CLI 参数](#cli-非交互参数)** ·
**[GUI 界面](#gui-界面)** ·
**[配置说明](#配置说明)** ·
**[目录结构](#数据与目录结构)** ·
**[公开 API](#公开-api-与版本策略)** ·
**[构建打包](#构建与打包)**

[中文](#中文文档) / [English](#english-docs)

---

## ✨ 核心特性

- **API 优先 + 浏览器回退** — 新闻走 httpx 直连 `content_v2_user` API，失败自动回退
  Playwright 拦截，再回退 HAR 文件，三重保障数据完整性
- **统一 SQLite 存储** — 所有抓取结果（新闻 / 发帖 / 微博 / 教程 / 图鉴）统一落库
  `data/toolkit.db`，唯一索引幂等去重，WAL 并发读写
- **pydantic-settings 配置** — `config.toml` 强类型配置，支持环境变量覆盖
  （`MIHOYO_` 前缀 + `__` 嵌套分隔符）
- **装饰器命令注册器** — `@registry.register(...)` 声明式注册，交互菜单与 GUI 共享命令清单
- **Qt MVC 图形界面** — PySide6 Model/View/Controller + QThread Worker，左导航 +
  内容区 + 底部全局日志，自动跟随系统深浅色主题，游戏字体主题化
- **分层架构** — core / scrapers / extractors / exporters / cli / gui / utils 职责清晰，易于扩展
- **工程质量** — ruff（lint + format）、mypy 渐进式类型检查、pytest 三层测试（覆盖率 ≥80%）
- **构建打包** — PyInstaller EXE / Docker 双模式 / GitHub Actions CI
- **增量更新** — 数据库唯一索引天然去重，`stop_on_existing` 命中即提前终止
- **Firefox 免登录 & HAR 回退** — 读取 Firefox Cookie 自动注入；接口失效时指引/加载 HAR

---

## 中文文档

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/vers123/mihoyo-tool-kit.git
cd mihoyo-tool-kit

# 2. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. 安装（可编辑安装 + 全部可选依赖）
pip install -e ".[dev,pinyin,excel,icon]"

# 4. 安装 Playwright 浏览器
playwright install chromium

# 5. 运行（三选一）
mihoyo-toolkit                # CLI 交互菜单（已安装的入口脚本）
python -m mihoyo_toolkit      # 等价的模块方式
mihoyo-toolkit --gui          # GUI 图形界面（或 python -m mihoyo_toolkit --gui）
```

> 源码运行也可直接用根级入口：`python run.py --gui`。

### 功能列表

CLI 模式启动后输入对应序号执行功能，输入 `0` 退出；GUI 模式通过左侧导航栏选择功能组。
共 **9 个分组、43 项功能**。

#### 米游社用户（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 1 | 抓取用户发帖主页 | 抓取米游社用户发帖主页并落库 |
| 2 | 增量抓取用户发帖 | 仅抓取新发帖，遇到已存在记录提前终止 |
| 3 | 提取用户发帖时间 | 从数据库导出用户发帖时间到 TXT |
| 4 | 增量提取用户发帖 | 增量导出用户发帖时间到 TXT |

#### 原神新闻（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 5 | 抓取新闻页面 | 抓取原神新闻页面并落库（约 4637 条） |
| 6 | 增量抓取新闻 | 增量抓取原神新闻并落库 |
| 7 | 提取新闻数据 | 导出原神新闻数据为 TXT |
| 8 | 增量提取新闻 | 增量导出原神新闻数据为 TXT |

#### 原神英文版新闻（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 9 | 抓取新闻页面 | 从 genshin.hoyoverse.com 抓取英文版新闻（约 2163 条） |
| 10 | 增量抓取新闻 | 增量抓取原神英文版新闻并落库 |
| 11 | 提取新闻数据 | 导出原神英文版新闻数据为 TXT |
| 12 | 增量提取新闻 | 增量导出原神英文版新闻数据为 TXT |

#### 绝区零新闻（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 13 | 抓取新闻页面 | 抓取绝区零新闻页面并落库（约 1554 条） |
| 14 | 增量抓取新闻 | 增量抓取绝区零新闻并落库 |
| 15 | 提取新闻数据 | 导出绝区零新闻数据为 TXT |
| 16 | 增量提取新闻 | 增量导出绝区零新闻数据为 TXT |

#### 星穹铁道新闻（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 17 | 抓取新闻页面 | 抓取星穹铁道新闻页面并落库（约 792 条） |
| 18 | 增量抓取新闻 | 增量抓取星穹铁道新闻并落库 |
| 19 | 提取新闻数据 | 导出星穹铁道新闻数据为 TXT |
| 20 | 增量提取新闻 | 增量导出星穹铁道新闻数据为 TXT |

#### 其他抓取（7 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 21 | 抓取角色图鉴页面 | 抓取米游社角色图鉴页面并落库 |
| 22 | 抓取单个教程页面 | 抓取指定教程详情页并落库角色数据（需输入教程 ID） |
| 23 | 批量抓取教程目录 | 从教程目录页提取链接并批量抓取 |
| 24 | 提取教程数据 | 解析教程 HTML 并导出角色数据 |
| 25 | 提取图鉴图片链接 | 从图鉴 HTML 提取图片链接并落库 |
| 26 | 抓取自定义网站 | 抓取任意 URL 并保存 HTML |
| 27 | 模型下载 | 下载角色模型资源 |

#### 微博（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 28 | 抓取微博用户主页 | 抓取微博用户主页并落库 |
| 29 | 增量抓取微博 | 仅抓取新微博，遇到已存在记录提前终止 |
| 30 | 提取微博数据 | 从数据库导出微博数据到 TXT |
| 31 | 增量提取微博数据 | 增量导出微博数据到 TXT |

#### 系统工具（8 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 32 | 查看备份文件 | 列出各数据源的备份文件 |
| 33 | 恢复备份数据 | 从备份文件恢复数据 |
| 34 | 查看当前配置 | 打印关键配置项 |
| 35 | 修改配置 | 交互修改 `config.toml` 中的常用字段 |
| 36 | 重新加载配置 | 清除缓存并重新读取 `config.toml` |
| 37 | 系统信息 | 打印运行环境与数据库统计 |
| 38 | 数据迁移工具 | 检查并按需迁移旧版 (v1) 数据目录 |
| 39 | 清理缓存 | 删除 `__pycache__` / `*.pyc` / 日志 / 构建产物（需 YES 确认） |

#### 数据导出（4 项）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 40 | 导出新闻到 Excel | 从 SQLite 导出四站点新闻到 `output/news.xlsx`（每站点一 sheet） |
| 41 | 导出 RSS Feed | 从 SQLite 生成 RSS 2.0 到 `output/news_feed.xml` |
| 42 | 导出 JSON Feed | 从 SQLite 生成 JSON Feed v1.2 到 `output/news_feed.json` |
| 43 | TXT 过滤 | 按关键词匹配提取行，支持精准/模糊匹配与时间排序 |

### CLI 非交互参数

除交互菜单外，`mihoyo-toolkit` 支持非交互执行（适合脚本 / Docker / CI）：

| 参数 | 取值 / 类型 | 说明 |
| ------ | ------ | ------ |
| `--fetch {genshin,genshin_en,zzz,starrail,all}` | 抓取 | 非交互抓取新闻（API 直连，不启动浏览器），`all` 逐站点增量抓取 |
| `--export-excel` | 开关 | 导出新闻到 Excel |
| `--export-feed {rss,json}` | 导出 | 导出 RSS / JSON Feed |
| `--count` | 开关 | 显示 SQLite 中各游戏新闻条数 |
| `--filter` | 开关 | 运行 TXT 过滤（交互式选择文件与关键词） |
| `--migrate` | 开关 | 运行旧版数据迁移检查 |
| `--gui` | 开关 | 启动图形界面 |
| `--version` | 开关 | 打印版本号 |

```bash
# 示例
mihoyo-toolkit --fetch all --export-excel --count
mihoyo-toolkit --export-feed rss
mihoyo-toolkit --version
```

### GUI 界面

GUI 采用 **PySide6** 框架，遵循 **MVC** 分层：

- **View** — `gui/pages/` 各功能页面（`BasePage` 提供统一的任务调度、进度条与结果表格）
- **Model** — `gui/models.py`（`GenericTableModel` / `NewsTableModel` / `MatchResultModel`）
- **Controller** — `gui/controllers.py`（`TaskController` 后台任务调度、`SystemController` 系统服务门面）
- **Worker** — `gui/workers.py`（`TaskWorker`，QThread + 信号，重定向 stdout/stderr 并按行转发）

**布局与特性：**

- **左侧导航 + 右侧内容区 + 底部全局日志面板**（`QSplitter` 可拖拽）
- **自动跟随系统深浅色主题**：启动时探测系统色彩方案（Qt `QStyleHints.colorScheme()`，
  Windows 下回退注册表 `AppsUseLightTheme`），并监听 `colorSchemeChanged`
  在系统切换主题时实时更新界面与日志配色
- **10 个导航项**：米游社用户、原神新闻、原神英文版新闻、绝区零新闻、星穹铁道新闻、
  其他抓取、微博、数据导出、TXT 过滤、系统工具
- **游戏字体主题化**：导航项使用各游戏专属字体（原神 Teyvat-Black、绝区零 ZZZ-System、
  星穹铁道 Star-Rail-Neue）
- **异步任务执行**：抓取 / 提取 / 导出 / 过滤在后台线程运行，界面不卡顿
- **进度条 + 停止按钮**：支持协作式取消（下次输出即中断）
- **全局日志**：页面输出统一汇总到底部面板，并同步写入 `logs/gui.log`
- **配置编辑**：系统工具页支持文本编辑 `config.toml`

```bash
mihoyo-toolkit --gui      # 或 Python: python -m mihoyo_toolkit --gui
```

#### 游戏字体资源

`resources/font/` 包含三款游戏的专属字体（每款提供 ttf / otf / woff2）：

| 游戏 | 字体 | GUI 用途 |
| ------ | ------ | ------ |
| 原神 | Teyvat-Black | 原神导航项标题字体 |
| 原神 | Deshret-Inscription / Font-Ainee / Inazuma-Brush / Khaenriah-Sun / Sumeru-Scribe | 装饰文字 |
| 绝区零 | ZZZ-System | 绝区零导航项标题字体 |
| 绝区零 | ZZZ-A | 绝区零正文字体 |
| 星穹铁道 | Star-Rail-Neue | 星穹铁道导航项标题字体 |
| 星穹铁道 | Xianzhou-Seal | 装饰文字 |

> 字体来源：[HoYo-Glyphs](https://github.com/SpeedyOrc-C/HoYo-Glyphs) · 仅供非商业用途，字体文件未做修改。完整许可见 `resources/font/LICENSE`。

### 配置说明

配置文件：`config.toml`（由 **pydantic-settings** 加载为强类型对象）。

```toml
[app]
mode = "cli"          # cli | gui
version = "2.1.1"

[fetch]
headless = true       # 浏览器后台运行
wait_seconds = 3      # 页面额外等待秒数
timeout = 120000      # 超时（毫秒）

[retry]
max_attempts = 3
delay = 2.0

[incremental]
enabled = true
stop_on_existing = true   # 命中已存在数据即终止
merge_data = true

[backup]
enabled = true
max_backups = 10

[cookies]
use_firefox = true    # 读取 Firefox cookie 免登录

[sources.user]
url = "https://www.miyoushe.com/ys/accountCenter/postList?id=75276539"

[sources.weibo]
url = "https://weibo.com/u/6593199887"

# [sources.baike] / [sources.news.genshin|genshin_en|zzz|starrail] ... 详见 config.toml
```

#### 环境变量覆盖

所有设置均可用环境变量覆盖，前缀 `MIHOYO_`，嵌套字段用双下划线 `__`：

```bash
MIHOYO_FETCH__HEADLESS=false          # 等价 [fetch].headless = false
MIHOYO_RETRY__MAX_ATTEMPTS=5          # 等价 [retry].max_attempts = 5
MIHOYO_SOURCES__USER__URL="..."       # 覆盖嵌套来源 URL
```

**加载优先级：** `init 参数 > 环境变量 > config.toml 文件`。

此外 `MIHOYO_HOME` 可覆盖项目根目录，`MIHOYO_DATA_DIR` 可覆盖数据目录。

### 数据与目录结构

```text
mihoyo-tool-kit/
├── pyproject.toml              # 可安装包声明 + ruff/mypy/pytest/coverage 配置
├── config.toml                 # 强类型配置文件（pydantic-settings）
├── run.py                      # PyInstaller 根级入口垫片（src/ layout 适配）
├── app.spec                    # PyInstaller spec
├── version_info.txt            # Windows 版本元数据
├── build.ps1 / build.bat / build.sh   # 构建脚本
├── Dockerfile                  # Docker（cli / full 双模式）
├── docs/
│   ├── architecture.md         # 架构文档
│   ├── reference.md            # AI Agent 模块/API 速查手册
│   └── create-plan.md          # 角色模型抓取计划
├── src/
│   └── mihoyo_toolkit/         # 包体（src/ layout）
│       ├── __init__.py         # 版本元信息（__version__ = "2.1.1"）
│       ├── __main__.py         # 双模式入口：CLI / --gui
│       ├── py.typed            # 类型标记
│       ├── core/               # 配置 / 路径 / 存储 / 模型 / 异常
│       │   ├── config.py       #   pydantic-settings 配置
│       │   ├── paths.py        #   PathManager 单例
│       │   ├── storage.py      #   统一 SQLite 存储层
│       │   ├── models.py       #   pydantic v2 数据模型
│       │   └── exceptions.py   #   异常层级
│       ├── scrapers/           # 抓取层
│       │   ├── base.py         #   抓取器基类（API 拦截 + HAR 回退）
│       │   ├── browser.py      #   Playwright 会话封装
│       │   ├── config.py       #   ScrapeConfig
│       │   ├── api_client.py   #   content_v2_user API 客户端（httpx）
│       │   ├── news/           #   四站点新闻抓取（base + 4 子类）
│       │   ├── user.py / weibo.py / baike.py / tutorial.py
│       │   └── custom.py / model_downloader.py
│       ├── extractors/         # 提取层（读库 → 导出 TXT）
│       │   ├── news/           #   新闻提取（base + 4 子类）
│       │   └── posts.py / weibo.py / images.py / tutorial.py
│       ├── exporters/          # 导出层
│       │   ├── excel_writer.py #   Excel 导出
│       │   └── feed.py         #   RSS / JSON Feed
│       ├── cli/                # 命令行
│       │   ├── registry.py     #   命令注册器
│       │   ├── commands.py     #   43 项命令定义
│       │   └── menu.py         #   交互式菜单
│       ├── gui/                # PySide6 MVC 图形界面
│       │   ├── main_window.py / models.py / controllers.py
│       │   ├── workers.py / widgets.py / theme.py / fonts.py / paths.py
│       │   └── pages/          #   各功能页面
│       └── utils/              # 工具层
│           ├── logger.py       #   三类日志
│           ├── har_loader.py   #   HAR 解析 / 回退
│           ├── cookie_loader.py#   Firefox Cookie
│           ├── backup_manager.py
│           ├── migration.py    #   旧版数据迁移
│           └── txt_filter.py   #   TXT 过滤
├── resources/                  # 游戏字体 + 应用图标（必须提交）
│   ├── font/                   #   游戏字体（Genshin Impact / Star Rail / ZenlessZoneZero）
│   └── icon/app.ico|app.png
├── data/                       # 运行期数据（自动创建，gitignore）
│   ├── toolkit.db              #   统一 SQLite 数据库
│   ├── html/                   #   抓取的 HTML（如 genshin_news.html）
│   ├── results/                #   提取导出的 TXT / 过滤结果
│   ├── images/                 #   图片链接导出
│   ├── models/                 #   下载的角色模型
│   └── backups/                #   自动备份
├── logs/                       # 日志（自动创建，gitignore）
├── har/                        # HAR 回退文件（自动创建，gitignore）
└── output/                     # 导出产物：news.xlsx / news_feed.xml|json
```

### 日志系统

运行时自动创建 `logs/`，日志按用途分为三类：

| 文件 | 内容 | 来源 |
| ------ | ------ | ------ |
| `logs/console.log` | 控制台全部输出 | `print()`、`stdout`/`stderr`（经 `_TeeStream` 镜像） |
| `logs/gui.log` | GUI 界面日志 | `append_gui_log()`，带时间戳、自动去重 |
| `logs/app.log` | 模块结构化日志 | `setup_logger()` / `get_module_logger()` 的 logging 输出 |

- `setup_console_log()` 用 `_TeeStream` 将 stdout/stderr 同时写终端与文件；
- `append_gui_log()` 供底部面板同步写入，已在消息内带时间戳时不重复添加；
- 模块日志由 `logging.FileHandler` 写入 `app.log`，同时经 `_LiveStdout` 代理输出到当前终端。

### HAR 回退与 Firefox Cookie

**HAR 回退** — 当 API 直连与 Playwright 拦截均无数据时，程序打印分步指引，引导从
Firefox 导出 HAR 文件；将 HAR 放入 `har/{scraper_name}/` 后重新运行即可解析复用。

| 抓取器 | HAR 目录 |
| ------ | ------ |
| 米游社用户发帖 | `har/user/` |
| 原神 / 原神英文版 / 绝区零 / 星穹铁道新闻 | `har/news_genshin/` · `har/news_genshin_en/` · `har/news_zzz/` · `har/news_starrail/` |
| 微博 | `har/weibo/` |
| 教程（中/英） | `har/tutorial/zh_cn/` · `har/tutorial/en_us/` |

**Firefox Cookie 免登录** — 在 Firefox 登录米游社 / 微博后，程序自动读取 Firefox 的
`cookies.sqlite` 并注入 Playwright，无需每次手动登录（由 `config.toml` 的
`[cookies].use_firefox` 控制）。

### 公开 API 与版本策略

本项目遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。按规范第 1 条，
**公开 API 已在 [`docs/public-api.md`](docs/public-api.md) 显式声明**，只有以下五个
面受版本号约束：

| 面 | 内容 |
| ------ | ------ |
| CLI 命令与参数 | 43 项命令的 `key` 与分组、`--fetch` / `--export-feed` 等参数取值 |
| Python 包 API | `core` / `scrapers` / `extractors` / `exporters` / `cli` / `gui` / `utils` 各自 `__all__` 列出的符号 |
| 配置格式 | `config.toml` 小节与字段、`MIHOYO_*` 环境变量与加载优先级 |
| 数据与目录约定 | `data/toolkit.db` 表结构、`data/html/{game}_news.html`、`data/results/*.txt`、`output/*`、`logs/*`、`har/*` |
| GUI 导航结构 | 由命令注册表派生的导航分组与顺序 |

未列入的模块与字段均视为内部实现。版本号规则：破坏上表任一面 → **MAJOR**；
向后兼容地新增（新命令、新配置项、新公开符号，或内部架构重大改进）→ **MINOR**；
向后兼容的修复与文档 → **PATCH**。已发布版本的内容不再修改。

### 构建与打包

#### Windows EXE（PyInstaller）

```powershell
.\build.ps1 deps            # 安装依赖 + Playwright 浏览器
.\build.ps1 exe-onedir      # 文件夹模式（推荐，启动快）
.\build.ps1 exe-onefile     # 单文件模式
```

产物位于 `dist/`（已含应用图标与版本信息）。EXE **不打包** Playwright 浏览器，
首次运行前需 `playwright install chromium`。

#### Docker

```bash
# CLI 模式（轻量：仅 API/CLI 依赖）
docker build -t mihoyo-toolkit .
docker run --rm -v $PWD/data:/app/data mihoyo-toolkit --fetch all --export-excel

# 完整模式（含 Playwright + PySide6；GUI 需 X11 转发）
docker build --build-arg MODE=full -t mihoyo-toolkit:full .
```

> 项目为 src/ layout，镜像内通过 `pip install -e .` 注册包与入口点（详见 Dockerfile 注释）。

#### 构建脚本命令

| 命令 | 说明 |
| ------ | ------ |
| `build.ps1 deps` | 安装依赖（`pip install -e ".[dev,pinyin,excel,icon]"` + Playwright chromium） |
| `build.ps1 test` | 运行 `pytest --cov --cov-report=term-missing` |
| `build.ps1 lint` | `ruff check .` + `ruff format --check .` |
| `build.ps1 type` | `mypy` 类型检查 |
| `build.ps1 exe-onefile` / `exe-onedir` | 打包单文件 / 文件夹模式 EXE |
| `build.ps1 docker` | 构建 Docker 镜像 |
| `build.ps1 clean` | 清理缓存（需输入 YES 确认） |
| `build.ps1 all` | `deps + lint + type + test + exe-onedir` |

`build.bat` 为 cmd 包装器，`build.sh` 为 Linux/macOS 等价实现。

#### CI

GitHub Actions（`.github/workflows/build.yml`）：

- **触发范围** — 仅 `main` 分支推送与 `v*` 标签触发；其他分支推送不会起流水线，
  向 `main` 提 Pull Request 会触发检查
- **test** — Python 3.11 / 3.12 / 3.13 矩阵测试 + 覆盖率
- **lint** — ruff check + format 检查
- **type** — mypy（失败即阻断流水线）
- **build-windows / build-docker** — tag 或 release 时构建 EXE / 镜像并上传产物
- **release** — 从 `CHANGELOG.md` 抽取对应版本段落，创建 GitHub Release 并附加产物

### 测试

```bash
pip install -e ".[dev]"
pytest --cov --cov-report=term-missing

pytest -m unit                  # 只跑单元测试
pytest -m integration           # 只跑集成测试
MIHOYO_E2E=1 pytest -m e2e      # 真实网络端到端（默认跳过，约 1s）
MIHOYO_E2E=1 MIHOYO_E2E_FULL=1 pytest -m e2e   # 追加完整分页（约 10s）
```

测试分为 `unit` / `integration` / `e2e` 三层（`e2e` 默认跳过），标记由
`tests/conftest.py` **按目录自动添加**，因此 `-m` 筛选开箱可用；e2e 默认档只发一次
请求，完整分页档由 `MIHOYO_E2E_FULL=1` 解锁。真实网络用例也可在 Actions 页面手动触发
`E2E (manual)` workflow（`scope` 选 `fast` / `full`，不随 push 自动运行）。覆盖率门槛
**≥80%**（按 `pyproject.toml` 的 coverage 配置，`gui/` 与 `__main__.py` 不计入；GUI 由
`tests/unit/test_gui_smoke.py` 做 offscreen 冒烟测试）。

---

## English Docs

### Quick Start

```bash
git clone https://github.com/vers123/mihoyo-tool-kit.git
cd mihoyo-tool-kit
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -e ".[dev,pinyin,excel,icon]"
playwright install chromium

mihoyo-toolkit                  # CLI interactive menu
python -m mihoyo_toolkit        # equivalent module form
mihoyo-toolkit --gui            # PySide6 GUI
```

### Core Features

- **API-first with browser fallback** — news uses the `content_v2_user` API over httpx;
  falls back to Playwright interception, then HAR files.
- **Unified SQLite storage** — all results (news/posts/weibo/tutorial/images) stored in
  `data/toolkit.db` with unique-index upserts and WAL mode.
- **pydantic-settings configuration** — typed `config.toml`, overridable via
  `MIHOYO_`-prefixed environment variables.
- **Decorator command registry** — `@registry.register(...)`; the CLI menu and GUI share
  one command catalogue.
- **Qt MVC GUI** — PySide6 Model/View/Controller + QThread workers; left navigation,
  content area and a global bottom log panel, themed with in-game fonts.
- **Layered architecture** — core / scrapers / extractors / exporters / cli / gui / utils.
- **Quality tooling** — ruff (lint + format), mypy, pytest with ≥80% coverage.
- **Packaging** — PyInstaller EXE, Docker (cli/full), GitHub Actions CI.

### Features

The toolkit ships **43 functions across 9 groups**: miyoushe user posts, Genshin (CN/EN) /
ZZZ / Star Rail news fetching & extraction, other scraping (baike / tutorial / custom /
model download), Weibo, system tools, and data export (Excel / RSS / JSON / TXT filter).

**News coverage** (unified `content_v2_user` API):

| Game | Endpoint | iChanId | Approx. total |
| ------ | ------ | :---: | :---: |
| Genshin Impact (CN) | `act-api-takumi-static.mihoyo.com` | 719 | 4,637 |
| Genshin Impact (EN) | `sg-public-api-static.hoyoverse.com` | 395 | 2,163 |
| Zenless Zone Zero | `api-takumi-static.mihoyo.com` | 273 | 1,554 |
| Star Rail | `act-api-takumi-static.mihoyo.com` | 255 | 792 |

### CLI Options

```bash
mihoyo-toolkit --fetch {genshin,genshin_en,zzz,starrail,all}
mihoyo-toolkit --export-excel
mihoyo-toolkit --export-feed {rss,json}
mihoyo-toolkit --count
mihoyo-toolkit --filter
mihoyo-toolkit --migrate
mihoyo-toolkit --gui
mihoyo-toolkit --version
```

### Configuration

Config file: `config.toml` (loaded via pydantic-settings). Any setting can be overridden
by an environment variable with the `MIHOYO_` prefix and `__` nesting, e.g.
`MIHOYO_FETCH__HEADLESS=false`. Precedence: `init > env > config.toml`.

### Build & Packaging

See [构建与打包](#构建与打包). Supports PyInstaller EXE (Windows), Docker (cli/full modes)
and GitHub Actions CI/CD.

> Game fonts are from [HoYo-Glyphs](https://github.com/SpeedyOrc-C/HoYo-Glyphs).
> For non-commercial use only. Font files are unmodified. See `resources/font/LICENSE`.

### Testing

```bash
pytest --cov --cov-report=term-missing
```

Three test tiers (`unit` / `integration` / `e2e`; `e2e` skipped by default), coverage ≥80%.

---

**V2.1.1** · Licensed under [MIT](LICENSE) · Maintained by LingLan · [Changelog](CHANGELOG.md)
