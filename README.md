# 米游社工具箱 / miHoYo ToolKit

> 基于 Playwright 的米游社 & 微博数据抓取工具 · 支持命令行与 GUI 双模式

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/versionV5.0.0-green)](Version)

**[快速开始](#快速开始)** ·
**[功能列表](#功能列表)** ·
**[GUI 界面](#gui-界面)** ·
**[配置说明](#配置说明)** ·
**[项目结构](#项目结构)**

[中文](#中文文档) / [English](#english-docs)

---

## ✨ 核心特性

- **四站点新闻抓取** — 原神中文（4637条）、原神英文（2163条）、绝区零（1554条）、星穹铁道（792条），统一 API 架构
- **双模式启动** — 命令行菜单（CLI）和 PySide6 图形界面（GUI）两种启动方式
- **游戏字体主题化** — GUI 使用各游戏专属字体（Teyvat-Black / ZZZ-System / Star-Rail-Neue）
- **API 拦截抓取** — 自动拦截浏览器 API 响应，绕过虚拟滚动，数据完整无遗漏
- **Firefox 免登录** — 读取 Firefox Cookie 自动注入，无需每次手动登录
- **HAR 智能回退** — API 检测失败时，自动指引提供 HAR 文件辅助分析
- **增量更新** — 检测已存在数据自动停止，支持合并与自动备份
- **模块化架构** — 抓取器 / 提取器分离，配置驱动，易于扩展

---

## 中文文档

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/vers123/miHoYo_ToolKit.git
cd miHoYo_ToolKit

# 2. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 4. 运行（二选一）
python main.py                 # CLI 命令行模式
python main.py --gui           # GUI 图形界面模式
```

### 功能列表

CLI 模式启动后输入对应序号执行功能，输入 `0` 退出。GUI 模式通过左侧导航栏选择功能组。

#### 米游社用户（CLI 1-4）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 1 | 抓取用户发帖主页 | 从米游社抓取指定用户的发帖记录 |
| 2 | 增量抓取用户发帖 | 增量更新用户发帖，自动备份旧数据 |
| 3 | 提取用户发帖时间 | 从用户主页提取发帖时间和标题 |
| 4 | 增量提取用户发帖 | 增量提取并合并新旧数据 |

#### 原神新闻（CLI 5-8）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 5 | 抓取原神新闻页面 | 从原神官网抓取新闻页面（4637条） |
| 6 | 增量抓取原神新闻 | 增量更新原神新闻，自动备份旧数据 |
| 7 | 提取原神新闻数据 | 从新闻页面提取标题和链接 |
| 8 | 增量提取原神新闻 | 增量提取并合并新旧数据 |

#### 原神英文版新闻（CLI 9-12）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 9 | 抓取原神英文版新闻 | 从 genshin.hoyoverse.com 抓取英文版新闻（2163条） |
| 10 | 增量抓取原神英文版新闻 | 增量更新原神英文版新闻，自动备份旧数据 |
| 11 | 提取原神英文版新闻数据 | 从新闻页面提取标题和链接 |
| 12 | 增量提取原神英文版新闻 | 增量提取并合并新旧数据 |

#### 绝区零新闻（CLI 13-16）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 13 | 抓取绝区零新闻页面 | 从绝区零官网抓取新闻页面（1554条） |
| 14 | 增量抓取绝区零新闻 | 增量更新绝区零新闻，自动备份旧数据 |
| 15 | 提取绝区零新闻数据 | 从新闻页面提取标题和链接 |
| 16 | 增量提取绝区零新闻 | 增量提取并合并新旧数据 |

#### 星穹铁道新闻（CLI 17-20）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 17 | 抓取星穹铁道新闻页面 | 从星穹铁道官网抓取新闻页面（792条） |
| 18 | 增量抓取星穹铁道新闻 | 增量更新星穹铁道新闻，自动备份旧数据 |
| 19 | 提取星穹铁道新闻数据 | 从新闻页面提取标题和链接 |
| 20 | 增量提取星穹铁道新闻 | 增量提取并合并新旧数据 |

#### 其他抓取（CLI 21-25）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 21 | 抓取角色图鉴页面 | 从米游社百科抓取角色图鉴信息 |
| 22 | 抓取米游社教程页面 | 从米游社抓取教程页面（需输入教程ID） |
| 23 | 提取教程角色数据 | 从教程页面提取角色编号和名称 |
| 24 | 提取图鉴图片链接 | 从抓取的图鉴页面提取角色图片链接 |
| 25 | 抓取自定义网站 | 抓取任意网站的HTML页面（需输入URL） |

#### 微博（CLI 26-29）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 26 | 抓取微博用户主页 | 从微博抓取指定用户的发帖记录 |
| 27 | 增量抓取微博用户 | 增量更新微博用户发帖，自动备份旧数据 |
| 28 | 提取微博数据 | 从微博页面提取发帖时间和内容 |
| 29 | 增量提取微博数据 | 增量提取并合并新旧微博数据 |

#### 系统工具（CLI 30-36）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 30 | 查看备份文件 | 查看所有数据备份文件 |
| 31 | 恢复备份数据 | 从备份文件恢复数据 |
| 32 | 查看当前配置 | 显示当前的配置信息 |
| 33 | 修改配置参数 | 修改URL、超时时间等配置 |
| 34 | 重新加载配置 | 从配置文件重新加载配置 |
| 35 | 系统信息 | 显示系统环境和依赖信息 |
| 36 | 数据迁移工具 | 迁移旧版本数据到新目录结构 |
| 0 | 退出程序 | 退出米游社工具箱 |

#### 数据导出（CLI 37-38）

| 序号 | 功能 | 说明 |
| :---: | ------ | ------ |
| 37 | 导出新闻到 Excel | 从 SQLite 导出四站点新闻到 .xlsx（每站点一 sheet） |
| 38 | 导出 RSS/JSON Feed | 从 SQLite 生成 RSS/JSON feed 供外部订阅 |

### GUI 界面

GUI 模式通过 `python main.py --gui` 启动，采用 **PySide6** 框架，左侧导航栏 + 右侧内容区 + 底部全局日志面板布局。

#### 启动方式

```bash
python main.py --gui     # 启动 GUI 图形界面
python main.py           # 启动 CLI 命令行（默认）
```

#### 界面特性

- **左侧导航栏** — 8 个功能组对应 CLI 的 8 个菜单分组
- **游戏字体主题化** — 导航项使用各游戏专属字体（原神 Teyvat-Black、绝区零 ZZZ-System、星穹铁道 Star-Rail-Neue）
- **浅色主题** — 搭配各游戏主题色（原神金色、绝区零橙色、星穹铁道青色）
- **全局底部日志面板** — 所有页面的 print() 输出统一显示，自动滚动、颜色高亮
- **异步任务执行** — 抓取/提取在后台线程（QThread）执行，界面不卡顿
- **进度条** — 确定进度条 + 百分比 + 文字进度
- **任务取消** — 支持"停止"按钮中断正在运行的任务
- **配置编辑** — 系统工具页提供文本编辑方式编辑配置文件

#### 游戏字体资源

`resources/font/` 目录包含四款游戏的专属字体，每款提供 ttf/otf/woff2 三种格式：

| 游戏 | 字体 | GUI 用途 |
| ------ | ------ | ------ |
| 原神 | Teyvat-Black | 原神导航项标题字体 |
| 原神 | Deshret-Inscription / Font-Ainee / Inazuma-Brush / Khaenriah-Sun / Sumeru-Scribe | 装饰文字 |
| 绝区零 | ZZZ-System | 绝区零导航项标题字体 |
| 绝区零 | ZZZ-A | 绝区零正文字体 |
| 星穹铁道 | Star-Rail-Neue | 星穹铁道导航项标题字体 |
| 星穹铁道 | Xianzhou-Seal | 装饰文字 |

> 字体来源：[HoYo-Glyphs](https://github.com/SpeedyOrc-C/HoYo-Glyphs) · 仅供非商业用途使用，字体文件未做修改。完整许可见 `resources/font/LICENSE`。

### 配置说明

配置文件：`config.json`

```json
{
  "user_url": "https://www.miyoushe.com/ys/accountCenter/postList?id=75276539",
  "baike_url": "https://baike.mihoyo.com/ys/obc/channel/map/189/25",
  "weibo_url": "https://weibo.com/u/6593199887",
  "headless": false,
  "wait_seconds": 3,
  "timeout": 120000,
  "weibo_settings": { "use_firefox_cookies": true },
  "miyoushe_settings": { "use_firefox_cookies": true },
  "news_sites": {
    "genshin":    { "url": "...", "iChanId": 719, "html_filename": "...", "data_filename": "..." },
    "genshin_en": { "url": "...", "iChanId": 395, "html_filename": "...", "data_filename": "..." },
    "zzz":        { "url": "...", "iChanId": 273, "html_filename": "...", "data_filename": "..." },
    "starrail":   { "url": "...", "iChanId": 255, "html_filename": "...", "data_filename": "..." }
  }
}
```

#### Cookie 免登录

在 Firefox 中登录米游社 / 微博后，程序自动读取 `cookies.sqlite` 并注入到 Playwright，无需手动登录。

#### HAR 回退

API 自动检测失败时，程序会打印详细步骤指引导出 HAR 文件。将 HAR 文件放入对应 `har/{scraper_name}/` 目录后重新运行即可。

> `har/` 目录及子目录会在首次使用时自动创建。

### 项目结构

```text
miHoYo_ToolKit/
├── main.py                    # 主程序入口（CLI + --gui 双模式）
├── config.json                # 配置文件
├── requirements.txt           # 依赖
├── Dockerfile                 # Docker 容器构建文件
├── core/                      # 核心模块
│   ├── scraper.py             # 抓取器基类（API拦截 + Cookie + HAR回退）
│   ├── config_manager.py      # 配置管理
│   ├── api_client.py          # API 直连客户端（非交互模式）
│   ├── storage.py             # SQLite 新闻存储
│   ├── feed.py                # RSS/JSON Feed 生成
│   └── models.py              # 数据模型
├── fetchers/                  # 抓取模块
│   ├── user.py                # 米游社用户发帖
│   ├── news/                  # 新闻抓取（基类 + 四站点子类）
│   │   ├── base.py            # 新闻抓取基类（content_v2_user API）
│   │   ├── genshin.py         # 原神新闻（中文）
│   │   ├── genshin_en.py      # 原神新闻（英文）
│   │   ├── zzz.py             # 绝区零新闻
│   │   └── starrail.py        # 星穹铁道新闻
│   ├── weibo.py               # 微博用户主页
│   ├── baike.py               # 角色图鉴
│   ├── tutorial.py            # 教程页面
│   └── custom.py              # 自定义网站
├── extractors/                # 提取模块
│   ├── time.py                # 发帖时间
│   ├── news/                  # 新闻提取（基类 + 四站点子类）
│   │   ├── base.py            # 新闻提取基类（7字段格式）
│   │   ├── genshin.py         # 原神新闻提取（中文）
│   │   ├── genshin_en.py      # 原神新闻提取（英文）
│   │   ├── zzz.py             # 绝区零新闻提取
│   │   └── starrail.py        # 星穹铁道新闻提取
│   ├── weibo.py               # 微博数据
│   ├── images.py              # 图片链接
│   ├── tutorial.py            # 教程数据
│   └── excel_writer.py        # Excel 导出
├── gui/                       # GUI 图形界面模块
│   ├── __init__.py            # launch_gui() 启动入口
│   ├── main_window.py         # 主窗口（左导航栏 + 内容区 + 底部日志面板）
│   ├── theme.py               # 浅色 QSS 主题 + 游戏字体加载
│   ├── workers.py             # QThread 异步任务 Worker
│   ├── widgets.py             # LogViewer 日志组件 + ProgressWidget 进度组件
│   └── pages/                 # 各功能页面
│       ├── news_page.py       # 新闻页面基类
│       ├── news_genshin.py    # 原神新闻页面
│       ├── news_genshin_en.py # 原神新闻页面（英文）
│       ├── news_zzz.py        # 绝区零新闻页面
│       ├── news_starrail.py   # 星穹铁道新闻页面
│       ├── user_posts.py      # 米游社用户页面
│       ├── other.py           # 其他抓取页面
│       ├── weibo.py           # 微博页面
│       └── system.py          # 系统工具页面
├── resources/font/            # 游戏字体资源
│   ├── Genshin Impact/        # 原神 6 款字体
│   ├── ZenlessZoneZero/       # 绝区零 2 款字体
│   └── Star Rail/             # 星穹铁道 2 款字体
├── utils/                     # 工具模块
│   ├── cookie_loader.py       # Firefox Cookie 读取
│   ├── har_loader.py          # HAR 文件解析
│   ├── backup_manager.py      # 备份管理
│   ├── error_handler.py       # 错误处理
│   ├── migration.py           # 数据迁移
│   └── logger.py              # 日志系统
├── tests/                     # 测试
├── data/                      # 输出数据（自动创建）
└── logs/                      # 日志（自动创建）
```

### 测试

```bash
python -m unittest tests.test_news -v
```

---

## English Docs

### Quick Start

```bash
# 1. Clone
git clone https://github.com/vers123/miHoYo_ToolKit.git
cd miHoYo_ToolKit

# 2. Create & activate venv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Run (choose one)
python main.py                 # CLI mode
python main.py --gui           # GUI mode
```

### Features

The toolkit supports 38 functions across 9 groups: miyoushe user posts, Genshin (CN/EN)/ZZZ/Star Rail news fetching & extraction, other scraping (baike/tutorial/custom), Weibo, system tools, and data export (Excel/RSS).

**News scraping coverage:**
- **Genshin Impact (CN)** — 4,637 articles via `act-api-takumi-static.mihoyo.com` (iChanId: 719)
- **Genshin Impact (EN)** — 2,163 articles via `sg-public-api-static.hoyoverse.com` (iChanId: 395, iAppId: 32)
- **Zenless Zone Zero** — 1,554 articles via `api-takumi-static.mihoyo.com` (iChanId: 273)
- **Star Rail** — 792 articles via `act-api-takumi-static.mihoyo.com` (iChanId: 255)

All four sites use the unified `content_v2_user` API architecture.

### GUI Mode

Launch the PySide6-based GUI with `python main.py --gui`. Features include left sidebar navigation, game-specific fonts (Teyvat-Black / ZZZ-System / Star-Rail-Neue), light theme with game accent colors, global bottom log panel, async task execution via QThread, and task cancellation support.

> Game fonts are from [HoYo-Glyphs](https://github.com/SpeedyOrc-C/HoYo-Glyphs). For non-commercial use only. Font files are unmodified. See `resources/font/LICENSE` for full license.

### Configuration

Config file: `config.json` — see [中文配置说明](#配置说明) for details.

### Project Structure

Same as the Chinese section above — see [项目结构](#项目结构).

### Testing

```bash
python -m unittest tests.test_news -v
```

---

**V5.0.0** · Licensed under [MIT](LICENSE) · Maintained by LingLan
