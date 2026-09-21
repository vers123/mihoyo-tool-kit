# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-09-22

GUI 启动欢迎弹窗改为可复制、链接可点击的自定义对话框，方便用户复制 URL 和目录去网站获取 HAR。

### Changed
- **GUI 启动欢迎弹窗**：由 `QMessageBox`（RichText，文本不可选中）替换为基于 `QTextBrowser` 的自定义 `QDialog`。
  - 弹窗内所有文本（URL、目录、操作步骤）现在支持鼠标选中和复制（Ctrl+C / 右键复制）。
  - 各网站页面 URL 改为可点击超链接，点击后在系统默认浏览器中打开，省去手动复制粘贴。
  - 弹窗尺寸调整为 620×560，内容区可滚动，底部「确定」按钮。
- **欢迎 HTML**：`utils/har_loader.py` 的 `get_har_welcome_html()` 将各网站 URL 由 `<code>` 纯文本改为 `<a href="...">` 超链接。

### Version
- **Version**: 1.1.1 → 1.2.0.

---

## [1.1.1] - 2026-09-19

修复增量更新后提取数据时覆盖本地历史数据文件的问题。

### Fixed
- **数据提取覆盖问题**：新闻（原神中/英、绝区零、星穹铁道）、微博、用户帖子提取器现在**始终将新提取数据与本地已有数据合并去重**后再写入，不再因 HTML 只含增量数据而覆盖完整历史。
  - 修复根因：此前 `incremental=False` 的提取路径只解析 HTML 中的数据并直接覆盖写入；增量抓取后 HTML 仅含新数据，导致历史丢失。
  - 新策略：只要本地数据文件存在，提取时一律合并新旧数据（按 URL 去重，新数据覆盖旧数据同 URL 项）。
  - 空数据保护：当 HTML 未解析到任何新数据但本地已有数据时，直接返回旧数据并跳过写入，保留原文件不变。
  - 涉及文件：`extractors/news/base.py`、`extractors/weibo.py`、`extractors/time.py`，以及 4 个新闻提取器的 `run` 函数。

### Changed
- **Version**: 1.1.0 → 1.1.1.

---

## [1.1.0] - 2026-09-19

TXT 过滤功能新增排序方向选择，用户可在时间降序（默认）与时间升序之间切换。

### Added
- **TXT 过滤排序方向选择**：CLI 与 GUI 均新增「排序方向」选项，支持「时间倒序（最新在前）」和「时间顺序（最早在前）」。
  - `extractors/txt_filter.py` 新增 `SORT_DESC` / `SORT_ASC` 常量与 `SORT_CHOICES`；`filter_and_sort()`、`run()`、`preview()` 均新增 `sort_order` 参数（默认 `SORT_DESC`）。
  - 无日期字段的行（角色列表、图片 URL 等）无论升降序始终排在末尾并保持原顺序。
- **CLI 交互**：在匹配模式选择后新增排序方向选择步骤（默认时间倒序）。
- **GUI 过滤页**：在匹配模式下拉框下方新增「排序方向」下拉框；预览对话框信息栏显示所选排序方向。

### Changed
- **Version**: 1.0.1 → 1.1.0.

---

## [1.0.1] - 2026-09-18

启动时增加 HAR 文件更新提示，引导用户在首次使用或接口失效时更新 Firefox HAR 捕获文件。

### Added
- **CLI 启动欢迎提示**：交互模式启动时打印欢迎语和 Firefox 导出 HAR 步骤，列出全部 6 个网站的页面 URL 与 HAR 保存目录，按回车继续。
- **GUI 启动欢迎弹窗**：主窗口显示前弹出 `QMessageBox`，含 HAR 更新步骤和各网站目录，点击「确定」后进入主窗口。
- **HAR 目录自动创建**：启动时自动创建所有缺失的 HAR 子目录（`har/user/`、`har/news_genshin_en/` 等）。
- **共享数据结构**：`utils/har_loader.py` 新增 `HAR_SITES` 常量、`ensure_har_dirs()`、`get_har_welcome_text()`、`get_har_welcome_html()`。

### Changed
- **Version**: 1.0.0 → 1.0.1.

---

## [1.0.0] - 2026-09-18

First stable release. Version number reset from 5.0.0 to 1.0.0.

### Release Highlights

- **40 CLI functions** across 9 groups, plus PySide6 GUI
- **TXT filter** with exact/fuzzy matching, preview dialog, and time-based renumbering
- **Weibo full pagination** via `since_id` cursor — fetches all posts back to 2019
- **Native GUI style** (PySide6 platform style) with application icon
- **Build system**: PyInstaller EXE, Docker (cli/full), GitHub Actions CI/CD
- **Cleanup**: CLI + build script cache cleaning with confirmation

### Added
- **GUI window icon**: application icon (`resources/icon/app.ico`, multi-size 16/32/48/64/128/256).
- **TXT filter preview**: GUI preview dialog with table view (new index, original index, title, date, category, matched keywords, source file) and confirm/modify/cancel actions.
- **TXT filter match modes**: exact (full substring) and fuzzy (2-gram fragment) matching, selectable in both CLI and GUI.
- **TQDM progress bars**: weibo, news, user posts, custom scraper now show live progress.
- **Build system**: PyInstaller spec (`app.spec`), version metadata (`version_info.txt`), cross-platform build scripts (`build.ps1`/`build.bat`/`build.sh`), Docker dual-mode (`cli`/`full`), GitHub Actions CI/CD.
- **Cleanup**: CLI menu option 40 and build script `clean` command, both require `YES` confirmation.
- **CHANGELOG.md**: version history document.

### Changed
- **GUI style**: switched from custom `LIGHT_QSS` theme to PySide6 native platform style. Font utilities moved to `gui/fonts.py`.
- **TXT filter keyword logic**: changed from AND to OR (any keyword hits).
- **Version**: reset from `5.0.0` to `1.0.0`.

### Fixed
- **Weibo scraper**: `bid` field no longer returned by API; now uses `mblogid` (with fallback to `bid`/`mid`/`idstr`).
- **Weibo pagination**: use API `since_id` cursor instead of `page`-only to reach the earliest posts.
- **Weibo date parsing**: support English format `Tue Dec 31 12:04:22 +0800 2019` → `YYYY-MM-DD HH:MM:SS`.
- **Pagination limits**: removed artificial `max_pages` / `max_scrolls` caps across all scrapers; rely on API/scroll termination signals.
- **Cross-drive path**: `os.path.relpath` failure on different drives handled gracefully.

### Removed
- `gui/theme.py` (custom QSS theme).

---

## [5.0.0] - (previous)

### Changed
- News storage moved to SQLite (`data/news.db`); data files retained for human reading.
- Auto-migration of pre-V5 filenames via `utils/migration.py`.
- 7-field `NewsItem` introduced; 4-field legacy read-only.

### Added
- Non-interactive CLI path: `--fetch` / `--export-excel` / `--count` + `core/api_client.py`.

---

## Pre-V5

- Flat `data/` layout, single news file per site, no SQLite, no GUI.
