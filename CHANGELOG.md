# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-04

米游社工具箱初始发布版本。整合米游社、微博数据抓取与提取功能，提供 CLI 与 PySide6 GUI 双界面，支持教程双语抓取、TXT 过滤、Excel 导出、RSS 订阅等。

### Release Highlights

- **40+ CLI 功能**（9 大分组）+ PySide6 图形界面
- **多站点抓取**：米游社用户发帖、角色百科、微博、四站点新闻（原神中/英、绝区零、星穹铁道）、教程页面
- **教程双语支持**：中文/英文教程抓取与提取，HTML 保存到子目录
- **TXT 过滤**：精确/模糊匹配、预览对话框、时间排序方向选择
- **微博全量分页**：基于 `since_id` 游标抓取全部历史帖子
- **数据安全**：增量提取自动合并本地历史，不覆盖已有数据
- **浏览器后台运行**：默认无头模式，Cookie 失效时自动弹出可见浏览器供登录
- **构建系统**：PyInstaller 打包、Docker 双模式、GitHub Actions CI/CD

### Added

- **多站点抓取器**
  - 米游社用户发帖（API 拦截 + HAR 回退，支持增量模式）
  - 米游社角色百科
  - 微博用户主页（AJAX API + HAR 回退，Firefox Cookie 登录）
  - 四站点新闻（原神中/英、绝区零、星穹铁道，API 拦截 + HAR 回退）
  - 教程页面（支持中英文双语、批量抓取目录）
  - 自定义 URL 抓取
- **数据提取器**：帖子、角色、新闻、微博、教程提取，自动合并本地历史数据
- **TXT 过滤**：精确匹配（子串）/ 模糊匹配（2-gram 片段），预览对话框（表格视图），时间排序方向（升序/降序）
- **Excel 导出**：懒加载 openpyxl，可选导出
- **RSS 订阅**：从 SQLite 读取新闻生成 RSS 2.0 / JSON Feed v1.2
- **GUI 图形界面**：PySide6 原生样式，多标签页（抓取/提取/过滤/系统信息）
- **GUI 欢迎弹窗**：可复制文本、可点击超链接的 HAR 更新指引
- **GUI 进度条**：批量抓取实时进度显示
- **HAR 文件管理**：自动创建 HAR 目录、检测并加载 HAR 回退
- **Firefox Cookie 加载**：微博/米游社支持从 Firefox 加载 Cookie 免登录
- **增量抓取**：`stop_on_existing` 提前终止 + 新旧数据合并去重
- **TQDM 进度条**：微博、新闻、用户发帖、自定义抓取实时进度
- **构建系统**：PyInstaller spec（`app.spec`）、版本元数据（`version_info.txt`）、跨平台构建脚本（`build.ps1`/`build.bat`/`build.sh`）、Docker 双模式（`cli`/`full`）、GitHub Actions CI/CD
- **缓存清理**：CLI 菜单 + 构建脚本 `clean` 命令，需 `YES` 确认

### Changed

- **浏览器默认后台运行**：所有抓取器默认 `headless=True`，不再弹出浏览器窗口
- **微博登录流程**：Cookie 失效时自动从无头模式切换到可见浏览器，提示用户登录后继续抓取
- **教程 HTML 保存路径**：统一保存到 `data/html/tutorial/` 子文件夹
- **教程文件名语言后缀**：选择语言后追加 `_zh-cn` / `_en-us` 后缀
- **GUI 样式**：PySide6 原生平台样式，无自定义 QSS 主题
- **TXT 过滤关键词逻辑**：AND 改为 OR（任一关键词命中即可）
- **数据提取策略**：始终将新数据与本地已有数据合并去重后写入

### Fixed

- **微博 ID 解析**：API 不再返回 `bid`，改用 `mblogid`（兼容 `bid`/`mid`/`idstr` 回退）
- **微博分页**：使用 `since_id` 游标而非仅 `page` 参数，确保抓取到最早帖子
- **微博日期解析**：支持英文格式 `Tue Dec 31 12:04:22 +0800 2019`
- **分页上限**：移除所有抓取器的人工 `max_pages` / `max_scrolls` 上限，依赖 API/滚动终止信号
- **跨盘符路径**：`os.path.relpath` 在不同盘符下失败时优雅处理
- **数据覆盖问题**：增量提取不再因 HTML 仅含新数据而覆盖完整历史

### Version

- **Version**: 1.0.0 (Initial release following Semantic Versioning).
