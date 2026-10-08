# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed

- **三层测试标记名不副实**：`pyproject.toml` 声明了 `unit` / `integration` / `e2e`，
  但只有 `tests/e2e/` 手写了 `pytestmark`，`pytest -m unit` 与 `-m integration`
  实际**一个用例都选不到**。现由 `tests/conftest.py` 的
  `pytest_collection_modifyitems` 钩子按目录自动打标（`unit` 252 / `integration` 67 /
  `e2e` 2，合计 321 全覆盖），并把根目录下的 `tests/test_cli.py` 移入
  `tests/integration/`，使每个测试文件都归属某一层。

### Added

- **`E2E (manual)` workflow**（`.github/workflows/e2e.yml`）：`workflow_dispatch` 手动
  触发真实网络端到端测试（`MIHOYO_E2E=1 pytest tests/e2e -m e2e`）。它不随 push 自动
  运行，常规 CI 仍只由 `main` 与 `v*` 标签触发；e2e 用例只用 httpx，无需安装浏览器。

### Docs

- `docs/architecture.md` §10、`CONTRIBUTING.md`、README 的测试章节改为说明「标记按目录
  自动添加」，并给出 `-m unit` / `-m integration` / `-m e2e` 的用法与手动 e2e 入口。

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
