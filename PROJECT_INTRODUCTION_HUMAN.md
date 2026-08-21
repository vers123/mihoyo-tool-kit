# 米游社工具箱（miHoYo ToolKit）完整项目介绍

## 一、项目基本信息

| 项目属性 | 详细内容 |
| -------- | -------- |
| 项目名称 | 米游社工具箱（miHoYo ToolKit） |
| 项目版本 | 代码版本 v2.1.0，README 标注 RV1.0.0 |
| 开源协议 | MIT License（版权所有：2026 昤兰） |
| 编程语言 | Python（要求 Python 3.8 及以上） |
| 核心技术 | Playwright（版本要求 ≥ 1.40.0，使用 Chromium 浏览器驱动） |
| 运行模式 | 命令行交互式菜单程序（非 Web 服务，非后台守护进程） |
| 维护者 | LingLan（昤兰） |
| 项目仓库 | https://github.com/vers123/miHoYo_ToolKit |

## 二、项目定位与核心目标

米游社工具箱是一款面向米哈游（miHoYo）旗下游戏社区和微博平台的数据采集与信息提取工具。项目的核心目标是：**将分散在米游社（Miyoushe）官网、原神官网、微博等动态网页上的公开内容，通过浏览器自动化技术完整采集下来，并从原始 HTML 中提取结构化的文本数据供用户留存或进一步分析。**

该工具解决了以下实际问题：

1. **虚拟滚动数据采集难题**：现代前端页面大量使用"滚动加载"和"无限下拉"设计，传统的 HTTP 请求抓取无法获取完整数据。本工具通过 Playwright 驱动真实浏览器模拟用户滚动操作，并拦截页面内部的 AJAX API 响应，实现数据的完整抓取。
2. **登录态复用难题**：抓取用户自己的主页或需要登录才能查看的内容时，每次运行都手动输入账号密码既麻烦又不安全。本工具直接读取 Firefox 浏览器的本地 Cookie 数据库（`cookies.sqlite`），将登录 Cookie 注入 Playwright 浏览器上下文，实现免登录抓取。
3. **API 结构变化的容错难题**：网站升级改版时后端 API 接口可能变化，导致自动检测失败。本工具设计了 HAR（HTTP Archive）回退机制，当 API 自动检测失败时，指导用户从浏览器开发者工具导出 HAR 文件，后续运行时程序会自动读取 HAR 中的 API 模式，实现灵活兼容。
4. **数据重复抓取与版本保护**：定期抓取同一页面会产生大量重复数据，且覆盖旧文件有数据丢失风险。本工具提供增量更新模式（检测到已存在的数据自动停止滚动）和自动备份机制（每次保存新数据前将旧文件复制到备份目录，最多保留 10 份历史版本），兼顾效率与安全。

## 三、系统功能详细清单

程序启动后显示交互式文本菜单，用户输入功能序号（1–23）执行对应操作，输入 `0` 退出。以下是全部 23 项功能的逐一说明。

### 3.1 抓取类功能（功能 1、2、3、4、5、6、8、14、15）

抓取类功能负责调用 Playwright 浏览器访问目标网页，滚动至底部以加载全部动态内容，最终将完整的 DOM 结构保存为本地 HTML 文件。保存位置由 `config.json` 中的 `output_dirs.html` 配置项决定，默认为 `data/html/` 目录。

| 功能序号 | 功能名称 | 抓取目标 URL 来源 | 输出文件名 | 支持增量模式 | 支持 Cookie 注入 | 支持 API 拦截 |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| 1 | 抓取用户发帖主页 | 配置文件 `user_url`，默认 `https://www.miyoushe.com/ys/accountCenter/postList?id=75276539` | `user_posts.html` | 否 | 是（米游社 Cookie） | 是（匹配 `userPostList` / `postList` API） |
| 2 | 增量抓取用户发帖 | 同功能 1 | 同功能 1 | 是 | 是 | 是 |
| 3 | 抓取角色图鉴页面 | 配置文件 `baike_url`，默认 `https://baike.mihoyo.com/ys/obc/channel/map/189/25` | `character_list.html` | 否 | 否 | 否（纯 DOM 抓取） |
| 4 | 抓取原神新闻页面 | 硬编码为 `https://ys.mihoyo.com/main/news` | `news_page.html` | 否 | 是（米游社 Cookie） | 是（匹配 `newsList` / `getNewsList` / `news` / `getList` / `postList` API） |
| 5 | 增量抓取原神新闻 | 同功能 4 | 同功能 4 | 是 | 是 | 是 |
| 6 | 抓取米游社教程页面 | 运行时用户输入教程 ID，默认 `mh4imrrhzdzi`，拼接为 `https://act.mihoyo.com/ys/ugc/tutorial/detail/{tutorial_id}` | `tutorial_{tutorial_id}.html` | 否 | 否 | 否（纯 DOM 抓取） |
| 8 | 抓取自定义网站 | 运行时用户输入任意 URL | 运行时用户指定，默认 `custom_page.html` | 否 | 否 | 否（纯 DOM 抓取） |
| 14 | 抓取微博用户主页 | 配置文件 `weibo_url`，默认 `https://weibo.com/u/6593199887`，并从 URL 中正则提取用户 ID | `weibo_posts.html` | 否 | 是（微博 Cookie） | 是（直接请求 `https://weibo.com/ajax/statuses/mymblog` 分页 API） |
| 15 | 增量抓取微博用户 | 同功能 14 | 同功能 14 | 是 | 是 | 是 |

#### 3.1.1 抓取流程的技术细节

每个抓取功能都遵循以下流程：

1. **构造配置**：根据功能类型实例化 `ScraperConfig` 数据类，填充 URL、输出文件名、浏览器参数、滚动延迟等字段。
2. **启动浏览器**：调用 `playwright.chromium.launch()` 启动 Chromium。若配置了 `--start-maximized` 则浏览器以最大化窗口可见方式打开（`headless=false` 时），否则在后台无头运行。
3. **注入 Cookie**：如果该抓取器启用了 Firefox Cookie（`use_firefox_cookies=true` 且配置了 `api_domain_filter`），则调用 `load_firefox_cookies()` 读取 Firefox `cookies.sqlite`，将匹配域名的 Cookie 注入 Playwright 的 `BrowserContext`。
4. **注册 API 拦截器**：对 User/News/Weibo 三类抓取器，通过 `page.on('response', handle_response)` 注册响应监听器，当响应 URL 命中 `api_url_keywords` 关键词列表时自动解析 JSON 响应并提取数据项。
5. **加载页面**：调用 `page.goto()` 跳转目标 URL，等待 `networkidle` 状态后再额外睡眠 `wait_seconds` 秒（默认 3 秒），确保页面框架渲染完毕。
6. **滚动加载**：循环执行 `window.scrollTo(0, document.body.scrollHeight)`，每次滚动后睡眠 `scroll_delay` 秒（默认 2 秒）。连续 3 次（Weibo/WebScraper 为 5 次）滚动后页面高度未增加，则判定已到达底部，停止滚动。
7. **增量停止判定**：增量模式下，每次滚动后还会执行 `_check_existing_urls()`：在浏览器内执行 JS 选择器获取当前页面所有文章链接，与本地已有的 URL 集合取交集，如发现任何已存在 URL 则立即停止后续滚动。
8. **结果处理**：优先使用 API 拦截收集到的数据（通过 `_build_html_from_api_data()` 将结构化数据转换回与页面 DOM 结构一致的 HTML，保证下游提取器兼容）；若 API 拦截未获取到数据，则回退到 `page.content()` 直接获取 DOM HTML。
9. **保存文件**：将最终 HTML 写入 `data/html/{output_filename}`。

微博抓取器有特殊的 API 流程：不依赖 response 拦截，而是在页面加载完成并确认登录成功后，直接使用 `page.request` 构造 `GET https://weibo.com/ajax/statuses/mymblog?uid={uid}&page={page}&feature=0` 请求，带上 Referer、X-Requested-With、X-XSRF-TOKEN 等请求头逐页抓取（最多 500 页），每 100 条打印一次进度，直至返回空列表或命中增量停止条件。

### 3.2 提取类功能（功能 7、9、10、11、12、13、16、17）

提取类功能读取 3.1 节抓取器保存下来的本地 HTML 文件，使用正则表达式从 HTML 中解析出结构化字段，并以固定文本格式保存到 `data/results/` 目录下。所有提取器在保存新数据之前，如果配置 `backup_settings.enabled=true` 且目标文件已存在，会先通过 `backup_manager.create_backup()` 将旧文件备份。

| 功能序号 | 功能名称 | 输入 HTML 文件 | 提取字段 | 输出文件 | 支持增量合并 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 7 | 提取教程角色数据 | `tutorial_{tutorial_id}.html` | 角色编号（`char_id`，要求 ≥ 7 位数字）、角色名称（`char_name`） | `characters_{tutorial_id}.txt` | 否 |
| 9 | 提取图鉴图片链接 | `character_list.html` | 角色名（`name`）、角色头像图片 URL（`url`，匹配 `data-src` 属性，去掉查询参数仅保留文件主体 URL） | `image_urls.txt` | 否 |
| 10 | 提取用户发帖时间 | `user_posts.html` | 发帖日期（`date`）、帖子标题（`title`）、帖子完整 URL（`url`） | `posts.txt` | 否 |
| 11 | 增量提取用户发帖 | 同功能 10 | 同功能 10 | 同功能 10 | 是（按 URL 去重合并） |
| 12 | 提取原神新闻数据 | `news_page.html` | 新闻标题（`title`）、新闻 URL（`url`）、发布日期（`date`） | `news.txt` | 否 |
| 13 | 增量提取新闻数据 | 同功能 12 | 同功能 12 | 同功能 12 | 是（按 URL 去重合并） |
| 16 | 提取微博数据 | `weibo_posts.html` | 发博日期（`date`）、正文内容（`content`，去除 HTML 标签、反转义、压缩空白）、微博单条 URL（`url`） | `weibo.txt` | 否 |
| 17 | 增量提取微博数据 | 同功能 16 | 同功能 16 | 同功能 16 | 是（按 URL 去重合并） |

#### 3.2.1 提取输出的文本格式规范

- **帖子数据 `posts.txt`**：每行一条，格式 `{序号:04d}-{标题}-[{YYYY-MM-DD}]({完整URL})`，行与行之间用两个换行符（`\n\n`）分隔。
- **新闻数据 `news.txt`**：每行一条，格式 `{序号:04d}-{标题}-[{日期}]-({完整URL})`，行之间用单个换行符（`\n`）分隔。
- **微博数据 `weibo.txt`**：每行一条，格式 `{序号:04d}-{正文}-[{YYYY-MM-DD}]({完整URL})`，行之间用两个换行符（`\n\n`）分隔。
- **图片链接 `image_urls.txt`**：每行一条，格式 `{序号:04d}-{角色名}-[{完整图片URL}]`。
- **教程角色 `characters_{tutorial_id}.txt`**：每行一条，格式 `{序号:04d}-{角色编号}-{角色名}`，按角色编号升序排序。

#### 3.2.2 日期解析规则

提取器内置相对日期智能转换逻辑（基准时间为 `datetime.now()`，当前年份记为 `current_year`）：

| 页面显示样例 | 转换后输出 | 触发条件 |
| :--- | :--- | :--- |
| `2小时前` | `{current_year}-{mm}-{dd}`（当前时间减 2 小时对应的日期） | 字符串包含"小时前" |
| `25分钟前` | `{current_year}-{mm}-{dd}`（当前时间减 25 分钟） | 字符串包含"分钟前"（仅微博提取器） |
| `昨天` | `{current_year}-{mm}-{dd}`（当前日期减 1 天） | 字符串包含"昨天"（仅微博提取器） |
| `前天` | `{current_year}-{mm}-{dd}`（当前日期减 2 天） | 字符串包含"前天"（仅微博提取器） |
| `01-15` | `{current_year}-01-15` | 正则匹配 `\d{2}-\d{2}` 格式 |
| `2024-01-15` 或 `2024-01-15 · 来自xxx` | `2024-01-15` | 正则匹配 `\d{4}-\d{2}-\d{2}` 格式（` · ` 以后内容丢弃） |
| `1704067200`（Unix 时间戳） | 对应格式 `YYYY-MM-DD` 或 `YYYY/MM/DD` | 值为正整数且 > 1000000000（API 响应时间戳字段） |

#### 3.2.3 增量合并逻辑

支持增量的提取器在执行时：

1. 先调用 `load_existing_data()` 读取当前输出文件，解析所有行，恢复为 `PostData` / `NewsData` / `WeiboData` 数据类列表。
2. 再解析新的 HTML 得到新数据列表。
3. 调用 `_merge_data(old_data, new_data)`：以 URL 为 key 构造字典 `merged = {item.url: item for item in old_data}`，然后遍历新数据，同 URL 的覆盖（保证最新内容优先），不同 URL 的追加。
4. 合并后按日期降序排序，并重新编号。
5. 最后保存到文件（保存前备份旧文件）。

### 3.3 备份管理功能（功能 18、19）

| 功能序号 | 功能名称 | 具体行为 |
| :---: | :--- | :--- |
| 18 | 查看备份文件 | 分别列出 `posts.txt`、`news.txt`、`weibo.txt` 三个数据文件的所有备份。对每个备份显示序号、文件名、创建时间（`YYYY-MM-DD HH:MM:SS`）、文件大小（KB）、完整路径。无备份时显示"无备份文件"。 |
| 19 | 恢复备份数据 | 子菜单：1. 恢复帖子 2. 恢复新闻 3. 恢复微博 0. 返回。选定数据类型后列出该类型所有备份，用户输入序号后将对应备份文件 `shutil.copy2` 覆盖回 `data/results/` 下的原文件名。恢复前如果原目标文件存在，还会额外生成一个 `{原文件名}.before_restore_{YYYYMMDD_HHMMSS}` 的临时安全副本。 |

### 3.4 配置管理功能（功能 20、21、22）

| 功能序号 | 功能名称 | 具体行为 |
| :---: | :--- | :--- |
| 20 | 查看当前配置 | 打印以下配置项当前值：user_url、baike_url、weibo_url、headless、wait_seconds（秒）、timeout（毫秒）、retry_settings.max_attempts、incremental_settings.enabled、backup_settings.enabled、backup_settings.max_backups、config_path 完整路径。 |
| 21 | 修改配置参数 | 依次交互式提示输入：user_url、baike_url、weibo_url、wait_seconds（验证为整数才写入）。直接按回车保留原值。全部输入完毕后调用 `config_manager.save_config()` 将内存中配置序列化为 JSON 写回 `config.json`。 |
| 22 | 重新加载配置 | 调用 `config_manager.load_config()` 重新从磁盘读取配置文件，适用于用户手动编辑了 `config.json` 后不重启程序直接生效的场景。 |

### 3.5 系统信息（功能 23）

调用 Python 标准库打印运行环境诊断信息：

- **操作系统**：`platform.system()` + `platform.release()`（例如 `Linux 5.15.0`）
- **Python 版本**：`platform.python_version()`（例如 `3.11.4`）
- **工作目录**：`main.py` 所在目录的绝对路径
- **配置文件**：`config_manager.config_path` 绝对路径
- **Playwright 版本**：尝试从 `playwright._repo_version.version` 获取版本号，未安装则提示"Playwright: 未安装"

## 四、项目目录与模块架构

项目采用清晰的分层架构：**入口层 → 核心层 → 抓取层/提取层 → 工具层**，每个模块职责单一、依赖方向自上而下。

```
/workspace
├── main.py                    # 入口层：主程序类 MiHoYoToolKit，交互式菜单调度
├── config.json                # 配置文件（JSON 格式）
├── requirements.txt           # Python 依赖清单（仅 playwright>=1.40.0 一行）
├── LICENSE                    # MIT 开源协议
├── README.md                  # 项目说明（中英双语）
├── .gitignore                 # Git 忽略规则
├── core/                      # 核心层：抓取基类 + 配置管理
│   ├── __init__.py            # 对外导出 BaseScraper, ScraperConfig, ConfigManager, config_manager
│   ├── scraper.py             # 抓取基类 BaseScraper + 配置数据类 ScraperConfig
│   └── config_manager.py      # 配置管理器 ConfigManager + 全局单例 config_manager
├── fetchers/                  # 抓取层：6 个具体抓取器实现
│   ├── __init__.py            # 导出抓取类与 run() 函数
│   ├── user.py                # 米游社用户发帖抓取器 UserScraper
│   ├── news.py                # 原神官网新闻抓取器 NewsScraper
│   ├── weibo.py               # 微博用户主页抓取器 WeiboScraper
│   ├── baike.py               # 米游社百科角色图鉴抓取器 BaikeScraper
│   ├── tutorial.py            # 米游社教程页面抓取器 TutorialScraper
│   └── custom.py              # 任意自定义网站抓取器 CustomScraper
├── extractors/                # 提取层：5 个 HTML→结构化数据转换器
│   ├── __init__.py            # 导出提取类与 run() 函数
│   ├── time.py                # 米游社帖子提取器 PostExtractor（字段：标题/日期/URL）
│   ├── news.py                # 原神新闻提取器 NewsExtractor（字段：标题/日期/URL）
│   ├── weibo.py               # 微博数据提取器 WeiboExtractor（字段：正文/日期/URL）
│   ├── images.py              # 角色图鉴图片提取器 ImageExtractor（字段：角色名/图片URL）
│   └── tutorial.py            # 教程角色数据提取器 TutorialExtractor（字段：角色编号/角色名）
├── utils/                     # 工具层：跨模块通用能力
│   ├── __init__.py            # 导出装饰器和辅助函数
│   ├── logger.py              # 日志系统（文件+控制台双输出、按大小轮转、装饰器函数调用埋点）
│   ├── error_handler.py       # 错误处理装饰器 handle_errors、重试装饰器 retry、静态工具类 ErrorHandler
│   ├── backup_manager.py      # 备份管理器 BackupManager + 全局单例 backup_manager
│   ├── cookie_loader.py       # Firefox Cookie 读取器（SQLite → Playwright Cookie 格式）
│   └── har_loader.py          # HAR 文件解析、API 模式识别、导出步骤指引
└── tests/                     # 测试层：单元测试
    ├── __init__.py            # 空文件
    └── test_extractors.py     # unittest 测试套件（共 6 个测试用例）
```

### 4.1 各模块的调用关系

执行"增量抓取用户发帖"功能时的典型调用链：

```
main.py::MiHoYoToolKit._incremental_fetch_user_posts()
  └─> fetchers.user::run(incremental=True)
        ├─> @handle_errors 装饰器（全局异常捕获）
        ├─> @retry 装饰器（失败自动重试 3 次，间隔 2 秒）
        └─> UserScraper(incremental=True) 实例化
              ├─> PostExtractor().get_existing_urls()  ← extractors.time
              │     └─> load_existing_data() 读取 posts.txt
              ├─> ScraperConfig 构造（读取 config_manager 配置）
              └─> BaseScraper.run()  ← core.scraper
                    ├─> sync_playwright() 启动 Chromium
                    ├─> _setup_browser() 启动浏览器上下文
                    │     └─> load_firefox_cookies("miyoushe.com")  ← utils.cookie_loader
                    │           └─> 读取 Firefox cookies.sqlite
                    ├─> _process_page()（由 UserScraper 覆盖）
                    │     ├─> _setup_api_interception() 注册 response 监听器
                    │     ├─> page.goto() 跳转 + 等待 networkidle
                    │     ├─> _scroll_for_data() 循环滚动触发 API
                    │     ├─> 命中已存在 URL → _api_stop_requested = True 停止
                    │     ├─> API 数据为空时 → find_har_file("user") + print_har_instructions()  ← utils.har_loader
                    │     └─> 最终生成 HTML（API 数据转 HTML / page.content() 兜底）
                    └─> _save_html() 写入 data/html/user_posts.html
```

执行"增量提取用户发帖"功能时的典型调用链：

```
main.py::MiHoYoToolKit._incremental_extract_posts()
  └─> extractors.time::run(incremental=True)
        ├─> PostExtractor.extract_posts(incremental=True)
        │     ├─> ErrorHandler.validate_file_exists()  ← utils.error_handler
        │     ├─> 正则匹配 DOM 得到新数据列表
        │     ├─> incremental=True → load_existing_data() + _merge_data()
        │     └─> sorted(set(items)) 去重排序
        └─> PostExtractor.save_post_data(post_data)
              ├─> backup_manager.create_backup()  ← utils.backup_manager
              │     └─> 备份到 data/backups/posts/posts_{YYYYMMDD_HHMMSS}.txt
              └─> 写入 data/results/posts.txt
```

## 五、配置文件详解（config.json）

配置文件使用 JSON 格式，位于项目根目录。首次运行时若不存在则由 `ConfigManager._get_default_config()` 自动生成默认值。以下逐字段说明：

| 配置路径（点号分隔） | JSON 类型 | 默认值 | 字段说明 |
| :--- | :--- | :--- | :--- |
| `user_url` | string | `"https://www.miyoushe.com/ys/accountCenter/postList?id=75276539"` | 功能 1、2 抓取的米游社用户主页 URL |
| `baike_url` | string | `"https://baike.mihoyo.com/ys/obc/channel/map/189/25"` | 功能 3 抓取的原神角色图鉴 URL |
| `weibo_url` | string | `"https://weibo.com/u/6593199887"` | 功能 14、15 抓取的微博用户主页 URL（程序会用正则 `/u/(\d+)` 提取数字 UID） |
| `headless` | boolean | `false` | Playwright 浏览器是否无头运行。`false` 时弹出可见浏览器窗口，`true` 时在后台静默运行（生产部署推荐 `true`） |
| `wait_seconds` | integer | `3` | 页面 `networkidle` 之后额外等待的秒数，用于让前端 JS 完成首屏渲染 |
| `timeout` | integer | `120000` | Playwright `page.goto()` 的超时时间，单位毫秒（默认 120 秒） |
| `user_agent` | string | `"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"` | 浏览器 User-Agent 请求头 |
| `output_dirs.html` | string | `"data/html"` | 抓取到的原始 HTML 文件存放目录 |
| `output_dirs.images` | string | `"data/images"` | 提取出的图片链接列表文件存放目录 |
| `output_dirs.data` | string | `"data/results"` | 提取出的结构化结果文件（posts.txt、news.txt、weibo.txt 等）存放目录 |
| `filenames.user_html` | string | `"user_posts.html"` | 米游社用户主页 HTML 文件名 |
| `filenames.baike_html` | string | `"character_list.html"` | 角色图鉴 HTML 文件名 |
| `filenames.image_urls` | string | `"image_urls.txt"` | 角色图片链接输出文件名 |
| `filenames.posts_data` | string | `"posts.txt"` | 米游社帖子结构化数据文件名 |
| `filenames.weibo_html` | string | `"weibo_posts.html"` | 微博 HTML 文件名（config_manager 默认 dataclass 中定义，config.json 中省略时使用默认） |
| `filenames.weibo_data` | string | `"weibo.txt"` | 微博结构化数据文件名（同上） |
| `browser_args` | array[string] | `["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"]` | 传递给 Chromium 启动的命令行参数。`--no-sandbox` 用于 Docker/CI 等无沙箱环境；`--disable-dev-shm-usage` 规避 `/dev/shm` 过小导致 Chromium 崩溃 |
| `scroll_settings.delay` | number | `2.0` | 每次滚动之间的睡眠秒数，必须设置得比前端加载延迟大，否则会重复滚动导致 API 请求重复触发 |
| `scroll_settings.max_scroll_attempts` | integer | `50` | **（滚动设置保留字段）** 在 `BaseScraper._scroll_to_bottom` 实际使用"连续 3 次高度不变停止"策略，此数字未被引用 |
| `retry_settings.max_attempts` | integer | `3` | fetchers 层 `@retry` 装饰器的最大重试次数 |
| `retry_settings.delay` | number | `2.0` | 重试间隔秒数 |
| `incremental_settings.enabled` | boolean | `true` | 是否启用增量更新总开关。设为 `false` 后增量抓取/提取功能仍可被调用，但内部不会加载已有 URL 做去重/停止判定 |
| `incremental_settings.stop_on_existing` | boolean | `true` | 增量滚动时检测到已有 URL 是否立即停止。设为 `false` 则会一直滚到底部再在提取阶段去重（可能重复抓取更多数据，但更不容易漏掉中间新插入的数据） |
| `incremental_settings.merge_data` | boolean | `true` | 增量提取时是否将新旧数据按 URL 合并。设为 `false` 时提取器只输出本次从 HTML 中解析到的新数据，旧文件会被直接覆盖（因此备份功能务必保留开启） |
| `backup_settings.enabled` | boolean | `true` | 保存前是否自动备份旧数据。总开关。 |
| `backup_settings.max_backups` | integer | `10` | 每种数据文件保留的最大备份数量。超过后每次新备份会自动删除修改时间最早的旧备份。删除的是 `data/backups/{类型}/` 目录下以原文件名开头的文件。 |
| `backup_settings.backup_dir` | string | `"data/backups"` | 备份目录根路径。每种文件会在其下创建同名子目录（如 `data/backups/posts/` 存放 posts.txt 的所有历史版本） |
| `weibo_settings.use_firefox_cookies` | boolean | `true` | 微博抓取器是否尝试加载 Firefox Cookie（匹配域名 `weibo.com`） |
| `miyoushe_settings.use_firefox_cookies` | boolean | `true` | 米游社相关抓取器是否尝试加载 Firefox Cookie（匹配域名 `miyoushe.com`） |

## 六、运行环境依赖与安装步骤

### 6.1 硬性依赖

| 依赖 | 版本要求 | 安装方式 | 说明 |
| :--- | :--- | :--- | :--- |
| Python | 3.8 及以上 | 从 python.org 或系统包管理器安装 | 代码使用了 `from __future__ import annotations`、dataclasses、f-string 等 3.8 语法特性 |
| Playwright for Python | ≥ 1.40.0 | `pip install playwright` | 浏览器自动化驱动。**注意：Python 包安装后还需要执行 `playwright install chromium`**，这一步会下载 Chromium 浏览器二进制（约 150–200 MB） |
| 操作系统 | Windows / macOS / Linux | — | 脚本中已做跨平台兼容：清屏命令区分 `cls`/`clear`，路径全部使用 `os.path.*` 处理。但 **Firefox Cookie 自动读取功能只在 Windows 实现**（依赖 `%APPDATA%` 环境变量定位配置目录），在 Linux/macOS 上运行会打印"未找到 Firefox 配置文件"的警告并跳过 Cookie 注入 |

### 6.2 完整安装流程（官方推荐）

```bash
# 步骤 1：克隆仓库
git clone https://github.com/vers123/miHoYo_ToolKit.git
cd miHoYo_ToolKit

# 步骤 2：创建并激活 Python 虚拟环境（推荐）
python -m venv .venv
# Windows 激活：
.venv\Scripts\activate
# macOS / Linux 激活：
# source .venv/bin/activate

# 步骤 3：安装 Python 依赖
pip install -r requirements.txt

# 步骤 4：安装 Playwright 浏览器内核
playwright install chromium

# 步骤 5：运行程序
python main.py
```

### 6.3 可选依赖（启用 Cookie 免登录功能）

| 前置条件 | 说明 |
| :--- | :--- |
| 已安装 Firefox 浏览器并在 Firefox 中登录过米游社/微博 | 程序读取的是 Firefox 的 `cookies.sqlite` 数据库，和 Chrome/Edge 等其他浏览器不兼容 |
| 运行时 Firefox 完全退出 | SQLite 数据库在 Firefox 运行期间被锁定，若此时读取会失败。程序实现中采用了"先复制到临时文件再查询"的策略，但仍建议关闭 Firefox 后再运行本工具 |
| 正确的用户配置目录（Windows） | 默认查找路径为 `%APPDATA%\Mozilla\Firefox\Profiles\` 下名字包含 `default-release` 或 `default` 且包含 `cookies.sqlite` 的第一个子目录。如果找不到则遍历所有子目录选第一个存在 Cookie DB 的 |

### 6.4 可选依赖（启用 HAR 回退功能）

无需安装额外 Python 包，只需要用户浏览器具备开发者工具即可。HAR 回退的目录结构在首次运行触发 HAR 指引时会自动创建：
- `har/user/` — 存放米游社用户抓取器的 HAR 文件
- `har/news/` — 存放原神新闻抓取器的 HAR 文件
- `har/weibo/` — 存放微博抓取器的 HAR 文件

## 七、测试体系

项目内附单元测试位于 `tests/test_extractors.py`，使用 Python 标准库 `unittest` 框架，共 3 个测试类合计 6 个测试用例：

| 测试类 | 测试用例方法名 | 断言内容 |
| :--- | :--- | :--- |
| `TestImageExtractor` | `test_extract_image_urls()` | 从构造的两段角色图鉴 HTML 中提取出 2 条 ImageData，且顺序为反转后（后匹配到的在列表头部）；名称和 URL 字段与输入严格相等 |
| `TestImageExtractor` | `test_save_image_data()` | 写入临时目录后读取输出文件内容，确认包含两条 `{序号}-{角色名}-[{图片URL}]` 格式的行 |
| `TestPostExtractor` | `test_extract_posts()` | 从构造的帖子卡片 HTML 中提取出 1 条 PostData，title=测试帖子标题，date=2024-01-15，url=https://www.miyoushe.com/ys/article/123 |
| `TestPostExtractor` | `test_parse_date()` | 固定测试时间点 2024-01-20 12:00:00，分别验证 `2小时前` → 当日、`01-15` → 当年补全年、`2023-12-25` → 原样保留三种解析分支 |
| `TestConfigManager` | `test_config_loading()` | 在临时目录写入自定义 JSON 配置后构造 ConfigManager 实例，验证 `get()` 方法对 3 个字段读取均正确，且与写入值完全一致 |

执行命令：`python -m unittest tests.test_extractors -v`。测试用例全部基于临时目录和构造的 HTML 数据，不依赖真实网络或 Playwright 浏览器。

## 八、数据输出与文件目录约定

### 8.1 动态创建的目录

以下目录在首次使用时自动创建，已在 `.gitignore` 中被忽略，不会提交到版本库：

```
data/
├── html/                # 抓取器输出原始 HTML（功能 1、2、3、4、5、6、8、14、15）
├── images/              # 图片链接列表输出（功能 9）
├── results/             # 结构化数据输出（功能 7、10、11、12、13、16、17）
└── backups/             # 自动备份目录
    ├── posts/           # posts.txt 历史版本（posts_YYYYMMDD_HHMMSS.txt）
    ├── news/            # news.txt 历史版本
    └── weibo/           # weibo.txt 历史版本

har/
├── user/                # 米游社用户抓取器 HAR 文件
├── news/                # 新闻抓取器 HAR 文件
└── weibo/               # 微博抓取器 HAR 文件

logs/
└── app.log              # 日志文件（按 10 MB 轮转，最多保留 5 份）
```

### 8.2 日志系统说明

`utils/logger.py` 基于 Python 标准库 `logging` 实现：
- **双输出通道**：所有 INFO 及以上级别日志同时写入控制台（stdout）和文件（`logs/app.log`）。
- **格式**：`YYYY-MM-DD HH:MM:SS - logger名称 - LEVEL - 消息内容`。
- **文件轮转**：单个日志文件大小上限 10 MB（`max_bytes=10*1024*1024`），超过自动创建 `app.log.1`、`app.log.2`... 最多保留 5 份（`backup_count=5`）。
- **装饰器埋点**：`@log_function_call` 装饰器会在函数进入时打印"调用函数: xxx"，正常退出时打印"函数 xxx 执行成功"，抛异常时打印错误和堆栈后重新抛出。`main.py` 中 23 个功能的 handler 方法均应用了此装饰器。
- **耗时追踪**：`@log_execution_time` 装饰器记录函数执行耗时秒数（当前代码中未在主要路径上使用，作为可选能力保留）。

## 九、错误处理与容错机制

本项目在多个层面构建了纵深防御式的错误处理体系：

1. **装饰器层（`@handle_errors`）**：所有 `fetchers.*.run()` 和 `extractors.*.run()` 入口函数以及 `main.py` 中的 handler 方法均被此装饰器包裹。捕获 `FileNotFoundError` / `ConnectionError` / `TimeoutError` / 通用 `Exception`，打印"❌ 错误：类型 - 详情"并返回 `None`，不会让异常冒泡到主循环导致程序崩溃。
2. **重试层（`@retry`）**：应用于所有 `fetchers.*.run()`，默认 3 次重试、每次间隔 2 秒。连续 3 次全部失败后才抛出最后一次异常（会被外层 `@handle_errors` 捕获）。
3. **安全执行类（`ErrorHandler.safe_execute()`）**：静态方法，接收任意可调用对象与参数，try/except 包住后失败返回 `default_return`。
4. **文件/目录校验（`ErrorHandler.validate_file_exists()` / `validate_directory_exists()`）**：提取器在读取 HTML 前和写入结果前都会做前置校验。目录不存在时自动 `os.makedirs(exist_ok=True)` 创建并打印"📁 创建目录"提示。
5. **HAR 回退层**：API 拦截抓取失败时不直接报错退出，而是降级到 `page.content()` 抓取 DOM HTML 兜底，并打印 9 步 HAR 导出指引。下次运行时若检测到用户放置的 HAR 文件，会自动识别并提示。
6. **登录兜底层（微博专用）**：Cookie 注入后如果页面中检测不到 `.wbpro-scroller-item` 元素（说明 Cookie 已失效或未登录），程序进入 90 秒轮询等待状态，打印"请在浏览器中完成登录"提示，给予用户充足的手动扫码登录时间。90 秒内检测到内容即继续，超时则打印警告后仍尝试继续抓取。
7. **备份恢复安全层**：恢复备份时如果目标文件已存在，会在覆盖前额外生成 `{filename}.before_restore_{timestamp}` 的临时安全副本，防止恢复操作本身破坏现场。
8. **配置降级层**：`load_config()` 读取 JSON 时如果遇到格式错误、IO 错误或其他异常，会打印 WARN 并退回使用默认配置运行，不因为配置文件损坏导致程序完全无法启动。

## 十、安全与合规注意事项

1. **Cookie 敏感性**：`har/` 子目录中的 HAR 文件和 Firefox Cookie 均包含用户登录凭证。`.gitignore` 中已加入 `har/*/` 规则忽略该目录，但用户仍需自行注意不要将 `config.json`（如包含自定义 URL 中的私有 ID）、HAR 文件、`data/` 输出目录上传到公开仓库（`.gitignore` 也已忽略 `data/` 和 `logs/`）。
2. **频率控制**：请勿将本工具用于大规模、高频次的批量抓取。配置中默认滚动延迟 2 秒、微博 API 每页间隔 2 秒，已内置基本的礼貌间隔。如对抓取速度有特殊要求，请自行评估目标网站 robots.txt 和使用条款。
3. **用途限制**：本工具仅用于个人研究、数据归档和信息整理，请遵守《网络安全法》及相关法规。抓取到的公开内容版权仍归原平台与作者所有，未经许可不得用于商业性再分发。
4. **MIT 免责声明**：MIT 协议明确声明"THE SOFTWARE IS PROVIDED AS IS"，软件作者不对因使用本工具导致的账号封禁、数据损失等后果承担任何责任。

## 十一、版本信息

- README 中 Badge 标注的发布版本：**RV1.0.0**
- `main.py` 中 `MiHoYoToolKit.__init__()` 硬编码的代码版本：**2.1.0**（内部开发版本，功能与 RV1.0.0 对应）
- 开源协议生效时间：2026 年
- 版权署名：昤兰（LingLan）
