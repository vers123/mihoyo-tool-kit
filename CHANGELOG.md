# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

（暂无）

## [3.0.0] - 2026-10-08

提取结果目录结构的 **MAJOR** 版本：`data/results/` 下的 TXT 由平铺改为按来源分目录，
属「数据与目录约定」的破坏性变更（详见 `docs/public-api.md`）。

### Changed

- **提取 TXT 按来源分目录**（破坏性）：`data/results/` 下不再平铺，改为 ——
  - 新闻 → `genshin/zh-cn/genshin_news.txt`、`genshin/en-us/genshin_en_news.txt`、
    `zzz/zzz_news.txt`、`starrail/starrail_news.txt`
  - 发帖 → `user/posts.txt`；微博 → `weibo/weibo.txt`；图鉴图片链接 →
    `images/image_urls.txt`；教程 → `tutorial/characters_{id}.txt`、
    `tutorial/changelog_{id}.json`
  - TXT 过滤结果仍在 `results/filtered/`（保留源文件相对目录结构）
- **配置字段 `lang_subdir` → `results_subdir`**（破坏性）：由「语言子目录名」改为
  「`data/results` 下的相对子目录」，取值如 `genshin/zh-cn`、`genshin/en-us`、
  `zzz`、`starrail`。旧字段此前从未被实际使用（死配置）。
- **备份恢复目标随目录调整**：`_backup_target()` 按新的来源子目录解析
  （`posts.txt` → `results/user/posts.txt`，`genshin_news.txt` →
  `results/genshin/zh-cn/genshin_news.txt` 等）。

### Fixed

- **教程 HTML 存取路径两端不一致**：抓取端写入平铺的 `data/html/tutorial_*.html`，
  提取端却读取 `data/html/tutorial/tutorial_*.html`，导致刚抓取的教程无法提取。
  现统一为 `data/html/tutorial/`（抓取端经新增的 `ScrapeConfig.html_subdir` 落盘，
  提取端与批抓取跳过检查共用 `TUTORIAL_HTML_SUBDIR` 常量）。

### Removed

- **`data/images/` 目录与 `PathManager.images`**：该目录此前从未被写入（图片链接一直
  导出到 `results/`），属冗余目录。图片链接现统一为
  `data/results/images/image_urls.txt`；旧数据迁移中 `images/` 下的文件改由迁移工具
  落到 `results/images/`。
- **`TxtFilter` 对 `images/` 的扫描**：现仅扫描 `results/`。

### Notes

- 版本号由 2.1.3 升至 **3.0.0**（SemVer MAJOR，破坏「数据与目录约定」）。
- **升级提示**：旧版 `data/results/*.txt` 不会自动迁移，请重新执行「提取」命令
  （读库重导出）或按上表手动移入对应子目录。

## [2.1.3] - 2026-10-08

仓库清理与结构对齐的 **PATCH** 版本：无功能变化、无 API 变更。

### Fixed

- **README 目录树与实际结构不一致**：补上 `docs/public-api.md`、`gui/nav.py`
  （v2.1.0 新增的导航装配模块）、整个 `tests/` 三层结构，以及此前缺失的
  `.github/`。

### Changed

- **清理开发缓存与构建元数据**：删除 `src/mihoyo_toolkit.egg-info/`（editable 安装
  产生的构建元数据）、`__pycache__`、`.pytest_cache` / `.ruff_cache` / `.mypy_cache`
  / `.coverage` 与 pytest 会话临时目录；`data/`（抓取数据）、`har/`（HAR 回退文件）、
  `output/`（导出产物）、`.venv/`（本地环境）保持不动。

### Notes

- 全量功能体检通过：pytest `321 passed, 3 skipped`（覆盖率门槛 80% 通过）；包内
  **68 个模块全部可导入**；CLI 非交互命令 `--version` / `--help` / `--count` /
  `--migrate` / `--export-excel` / `--export-feed rss|json` 退出码均为 0 且导出产物
  正常刷新；交互菜单可启动并正常退出；本地真实网络 e2e `2 passed, 1 skipped`。

## [2.1.2] - 2026-10-08

清理行为的 PATCH 修复（Windows 文件占用）+ 测试基础设施收尾。

### Fixed

- **`system.clean` 删不掉日志（Windows 必现）**：`logs/app.log` 被本包 logger 的
  `logging.FileHandler` 持有、`logs/console.log` 被 `_TeeStream` 的镜像文件持有，
  清理时必然 `WinError 32`。现在删除前先释放这两类句柄，并复位 `_configured` 与
  `sys._mihoyo_console_configured`，后续日志调用会重新创建日志文件。实测：
  修复前「失败 1 个」，修复后「释放日志句柄 26 个，失败 0 个」。
- **每次 pytest 都在仓库里残留一个会话目录**：`tests/conftest.py` 的 `atexit`
  回调早于 `logging` 自身的 shutdown 执行，`logs/app.log` 仍被占用 → `rmtree`
  失败，而 `ignore_errors=True` 又把失败吞掉，只留下一个空壳目录（系统临时目录
  不可写时会落在仓库根）。现在先 `logging.shutdown()` 再删，并在会话开始时兜底
  清扫超过 1 小时的同名遗留目录（带年龄阈值，避免误删并发会话）。

### Changed

- **清理口径与构建脚本对齐**：`BUILD_DIRS` 增加 `.ruff_cache` / `.mypy_cache` /
  `htmlcov`，新增 `BUILD_FILES = (".coverage",)`，与 `build.ps1` / `build.sh` 的
  `clean` 一致 —— 此前 Python 清理不会碰这些开发缓存，两处口径不一致。

### Added

- **回归护栏**（`tests/integration/test_cli_clean.py`）：校验清理目标覆盖开发缓存与
  构建产物，并断言**被 logger 持有的 `logs/app.log` 仍会被删除**（该用例在 Windows
  修复前必失败）。
- `.gitignore` 增加 `mihoyo_toolkit_tests_*/`：会话临时目录此前只靠 `*.log` 规则
  偶然挡住，一旦进程被强杀留下 `config.toml` 就会出现在 `git status` 里。

## [2.1.1] - 2026-10-08

测试工具链与 CI 的补丁版本（**PATCH**）：无用户可见行为变化，无 API 变更。

### Changed

- **e2e 耗时从 6 分 34 秒降到秒级**：默认用例把站点配置的 `api_page_size` 调大，
  使 `fetch_all()` 的 `max_pages` 收敛为 1 —— **一次请求**即走完整条 `fetch_all()`
  路径（重试包装 / `iTotal` 处理 / 解析 / 循环退出，仍返回真实数据）；完整分页用例
  改为 `MIHOYO_E2E_FULL=1` 才执行，且每页取 API 实际上限 300，页数从上万级降到
  十几页。实测：默认档 `2 passed, 1 skipped in 1.25s`，完整档 `3 passed in 8.30s`。
- **`E2E (manual)` workflow 增加 `scope` 输入**（`fast` 默认 / `full`）：选 `full`
  时注入 `MIHOYO_E2E_FULL=1`，用于手动验证完整分页。

### Fixed

- **三层测试标记名不副实**：`pyproject.toml` 声明了 `unit` / `integration` / `e2e`，
  但只有 `tests/e2e/` 手写了 `pytestmark`，`pytest -m unit` 与 `-m integration`
  实际**一个用例都选不到**。现由 `tests/conftest.py` 的
  `pytest_collection_modifyitems` 钩子按目录自动打标（`unit` 252 / `integration` 67 /
  `e2e` 3，合计 322 全覆盖），并把根目录下的 `tests/test_cli.py` 移入
  `tests/integration/`，使每个测试文件都归属某一层。

### Added

- **`E2E (manual)` workflow**（`.github/workflows/e2e.yml`）：`workflow_dispatch` 手动
  触发真实网络端到端测试（`MIHOYO_E2E=1 pytest tests/e2e -m e2e`）。它不随 push 自动
  运行，常规 CI 仍只由 `main` 与 `v*` 标签触发；e2e 用例只用 httpx，无需安装浏览器。

### Docs

- `docs/architecture.md` §10、`CONTRIBUTING.md`、README 的测试章节改为说明「标记按目录
  自动添加」，给出 `-m unit` / `-m integration` / `-m e2e` 的用法，并写明 e2e 的
  fast（默认，1 次请求）与 full（`MIHOYO_E2E_FULL=1`，完整分页）两档及手动入口。

## [2.1.0] - 2026-10-08

向后兼容的功能新增 + v2.0.0 重构的工程质量收尾。按
[SemVer 2.0.0](https://semver.org/lang/zh-CN/)：本版为 **MINOR**（新增功能与内部重大
改进，无破坏性变更），并**首次显式声明公开 API**（见 [`docs/public-api.md`](docs/public-api.md)）。

### Changed

- **CI 触发范围收敛为主分支**：`on.push.branches` 由 `[main, master, "release/**"]`
  收窄为 `[main]`，只有主分支推送会触发 workflow；标签 `v*` 仍是唯一发布入口
  （2.0.1 中「扩展为 `release/**`」的做法已收回，见下方 Removed）。
- **覆盖率门槛落到实处**：门槛由 35% 提升为 **80%**，并把 coverage 配置统一到
  `pyproject.toml`（删除 `.coveragerc`）。此前 coverage 只读 `.coveragerc`，
  `pyproject.toml` 里的 `[tool.coverage.*]` 实际是死配置。
- **mypy 改为阻断 CI**：移除 type job 的 `continue-on-error: true`，类型错误会
  直接让流水线失败。

### Added

- **公开 API 声明**（`docs/public-api.md`）：按 SemVer 规范第 1 条显式划定公开接口
  ——CLI 命令与参数、Python 包公开符号、`config.toml` 与环境变量、数据与目录约定、
  GUI 导航结构，并写明 MAJOR / MINOR / PATCH 的判定规则。
- **GUI 导航改由命令注册表派生**（`gui/nav.py`）：`MainWindow` 不再硬编码导航清单，
  导航标题、分组顺序、组内命令均取自 `cli/registry.py`，界面与交互菜单从此真正共用
  同一份命令清单（v2.0.0 曾如此声称但未实现）；装配时校验每条命令**恰好**被一个
  页面负责，缺漏或重复即抛出新异常 `GuiError`。导航顺序随之与 CLI 菜单一致
  （`系统工具` 移到 `数据导出` 之前），页面集合与功能不变。
- **`core.exceptions.GuiError`**：GUI 装配错误（命令未映射到页面等），已纳入公开符号。
- **GUI 冒烟测试**（`tests/unit/test_gui_smoke.py`）：offscreen 下构建主窗口、校验导航
  覆盖全部 43 条注册命令、主题调色板与样式表可用、`TaskController` 后台线程执行与
  协作式取消可用。CI 的 test job 补装 Qt 无头运行库（`libegl1` / `libgl1` 等），
  使测试在 ubuntu 运行器上真正执行；环境确实无法加载 Qt 时自动跳过（pytest 8.2
  起 `importorskip` 不再吞掉此类 ImportError，故为显式捕获）。

### Removed

- **v1 分支 / 标签 / Release**：删除 `release/v1.0.1`、`release/v1.1.0`、
  `release/v1.1.1`、`release/v1.1.2`、`release/v2.0.0`、`release/v2.0.1` 分支，
  以及 `v1.0.0`、`v1.0.1`、`v1.1.0`、`v1.1.1` 标签与 `v1.0.0`、`v1.0.1` 两个
  Release。仓库仅保留 `main` 分支与 `v2.0.0`、`v2.0.1` 标签；v1 代码不再有
  命名引用（仅存于本地 reflog 与其他克隆）。
- **`.flake8`**：已被 ruff（`pyproject.toml`）取代的遗留配置。
- **`requirements.txt`**：内容与 `pyproject.toml` 重复且缺少 `pydantic-settings`
  （照它安装会得到无法启动的环境），依赖统一以 `pyproject.toml` 为单一来源。

### Docs

- **新增 `docs/public-api.md`**：公开 API 清单与版本号判定规则（本项目对 SemVer 的承诺）。
- `CONTRIBUTING.md` 重写为 v2：src/ layout、`pip install -e ".[dev,pinyin,excel,icon]"`、
  Python 3.11+、pytest 三层测试、`scrapers/` 与 `extractors/` 模块图、`config.toml`，
  并写明「只有 `main` 与 `v*` 标签触发 CI」。
- `docs/architecture.md`、`docs/reference.md` 版本号对齐到 2.1.0；「新增 GUI 页面」的
  步骤由 `NAV_ITEMS` 改为在 `gui/nav.py` 登记。
- README 增加「公开 API 与版本策略」章节与顶部索引链接，CI 章节补充触发范围与 mypy
  阻断说明，并注明覆盖率统计范围。

## [2.0.1] - 2026-10-08

CI / 发布流程补丁版本。功能与 2.0.0 完全一致，无 API 变更。

### Fixed

- **发布分支推送漏跑 CI**：`push` 与 `pull_request` 的触发分支由 `main` / `master`
  扩展为同时包含 `release/**`；此前只推 `release/*` 分支不会触发任何 workflow，
  只有 `v*` 标签才会运行。
- **版本号声明不一致**：`pyproject.toml`、`__init__.py`、`config.toml`、
  `core.config` 默认值、`version_info.txt`、`app.spec` 与 README 统一升至 2.0.1；
  HAR 欢迎语改为读取 `__version__`，不再硬编码版本号。

## [2.0.0] - 2026-10-08

架构级重构版本。功能层面完全对齐 v1.1.2（CLI 由 41 项扩充至 **43 项**），
内部从「脚本式 + 手写配置/存储/错误处理」重构为「可安装包 + 分层架构 +
强类型配置 + 统一存储」。旧版 import 别名与 `config.json` 不再保留。

### Changed

- **项目布局改为 src/ layout**：包体迁入 `src/mihoyo_toolkit/`，根目录以
  `pyproject.toml` 声明为 **可安装包**（`pip install -e .`），提供
  `mihoyo-toolkit`（CLI）与 `mihoyo-toolkit-gui`（GUI）两个入口脚本。
- **配置系统重写**：由 `config.json` + 手写 `ConfigManager` 改为
  **pydantic-settings + `config.toml`**，支持环境变量覆盖
  （前缀 `MIHOYO_`、嵌套分隔符 `__`，如 `MIHOYO_FETCH__HEADLESS=false`），
  加载优先级 `init > env > config.toml`。
- **存储统一为 SQLite**：由「新闻进 SQLite + 其他写 TXT」的混合方案改为
  **单文件 `data/toolkit.db`**（`news` / `posts` / `weibo` / `tutorial` / `images`
  五张表），以唯一索引实现幂等 upsert 与去重，WAL 模式提升并发读写。
- **数据模型升级为 pydantic v2**：原 dataclass `models` 改为 pydantic `BaseModel`
  （`NewsItem` / `PostItem` / `WeiboItem` / `TutorialItem` / `ImageItem`），
  自带校验、序列化与 snake_case 别名。
- **异常处理与重试重构**：由装饰器 `@handle_errors` 改为 **显式异常层级**
  （`MihoyoError` → `ConfigError` / `NetworkError`→`RetryExhausted`/`AuthError`
  / `ParseError` / `StorageError` / `ScraperError`）+ **tenacity** 指数退避重试。
- **CLI 命令改为装饰器注册器**：由 `main.py` 内字典硬编码菜单改为
  `@registry.register(...)` 声明式注册（`cli/registry.py`），交互菜单与 GUI
  共享同一份命令清单。
- **GUI 重构为 Qt MVC**：由页面内直接调用抓取逻辑改为
  **Model（`gui/models.py`）/ View（`gui/pages/*`）/ Controller（`gui/controllers.py`）
  + Worker（`gui/workers.py`，QThread + 信号）** 结构，耗时任务在后台线程执行，
  支持协作式取消。
- **GUI 主题自动跟随系统**：`gui/theme.py` 提供 `LIGHT` / `DARK` 双主题调色板，
  启动时经 Qt `QStyleHints.colorScheme()`（Windows 回退注册表 `AppsUseLightTheme`）
  探测系统深浅色，并监听 `colorSchemeChanged` 信号在系统切换主题时实时刷新
  界面样式与日志面板配色。
- **路径管理集中化**：新增 `PathManager` 单例（`core/paths.py`），统一解析
  `data` / `html` / `results` / `images` / `models` / `backups` / `logs` / `har`
  / `output` / `resources`，消除散落的 `os.path.join`。
- **保留三类日志**：`logs/console.log`（终端输出）、`logs/gui.log`（GUI 面板）、
  `logs/app.log`（logging 结构化日志）。
- **文件命名规范化**：新闻 HTML 统一为 `data/html/{game}_news.html`
  （`genshin` / `genshin_en` / `zzz` / `starrail`）。
- **抓取策略明确为三轨**：**API 直连优先（httpx）→ Playwright 拦截回退 →
  HAR 文件回退**。

### Added

- **`pyproject.toml` 可安装包**：声明运行依赖（httpx / tenacity / pydantic /
  pydantic-settings / tqdm / playwright / PySide6）与可选 extras
  （`pinyin` / `excel` / `icon` / `dev`）。
- **`docs/architecture.md`**：分层架构、数据流、抓取双轨时序、配置系统、
  SQLite schema、命令注册器、GUI MVC 与扩展指南。
- **`docs/reference.md`**：AI Agent 模块 / API 速查手册与常见任务配方。
- **质量工具配置**：ruff（lint + format）、mypy（渐进式类型检查），
  内置于 `pyproject.toml`。
- **pytest 三层测试**：`unit` / `integration` / `e2e` 标记，覆盖率门槛 **≥80%**。
- **构建与 CI 增强**：`build.ps1` / `build.bat` / `build.sh` 全面更新为
  `pip install -e`、`ruff` / `mypy` / `pytest`、`PYI_MODE` 打包；
  `Dockerfile` 支持 `cli` / `full` 双模式；GitHub Actions 增加 lint / mypy
  矩阵与 tag 触发的 EXE / Docker / Release 发布。
- **src/ layout 适配的 PyInstaller 入口**：新增根级 `run.py` 垫片与
  适配 src/ layout 的 `app.spec`。

### Removed

- **向后兼容别名**：移除 `run_extract_time`、`NewsExtractor` 等旧入口别名，
  调用方需使用 v2 公开 API（详见 `docs/reference.md`）。
- **`config.json`**：由 `config.toml` 取代。
- **分散的 TXT 写入路径**：抓取结果统一入 SQLite；TXT 仅由提取层从库导出，
  写入 `data/results/`。
- **v1 顶层模块树**：移除仓库根目录残留的 v1 实现（`main.py` 以及 `core/`、
  `utils/`、`extractors/`、`fetchers/`、`gui/`）与仅供其使用的旧测试，
  仓库结构与 README「数据与目录结构」一致；v1 代码仍可从 `v1.1.2` 标签取得。
- **`doc/ai/README.md`**：v1.0.0 时代的 AI 速查手册，已由 `docs/reference.md` 取代。

### Notes

- 功能与 v1.1.2 完全对齐，CLI 菜单项由 41 项调整为 **43 项**
  （9 个分组，详见 README「功能列表」）。
- 旧版 `data/` 目录可使用「系统工具 → 数据迁移工具」或 `--migrate` 迁移。
- 清理 v1 残留后 `ruff check .` 与 `ruff format --check .` 全绿（此前根目录
  60 个 v1 文件使 lint job 报 381 项）。
