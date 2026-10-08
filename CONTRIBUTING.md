# 贡献指南

感谢你对米游社工具箱的关注！以下是参与贡献的指南。

> 本指南对应 **v2.0.x**（src/ layout + pydantic-settings + 统一 SQLite）。
> v1.x 的顶层目录结构（`main.py`、`core/`、`fetchers/`、`config.json`）已不再存在。
>
> **CI 触发策略**：只有 `main` 分支的推送与 `v*` 标签会触发 GitHub Actions，
> 功能分支推送不会自动跑流水线（属正常现象）；向 `main` 提 Pull Request 会触发检查。

## 开发环境搭建

```bash
# 1. Fork 并克隆
git clone https://github.com/vers123/mihoyo-tool-kit.git
cd mihoyo-tool-kit

# 2. 虚拟环境（需要 Python 3.11+）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. 以可编辑方式安装（依赖只声明在 pyproject.toml）
pip install -e ".[dev,pinyin,excel,icon]"
playwright install chromium
```

## 项目结构

| 目录 | 职责 |
| ------ | ------ |
| `src/mihoyo_toolkit/core/` | 配置（pydantic-settings）/ 路径 / SQLite 存储 / 模型 / 异常 |
| `src/mihoyo_toolkit/scrapers/` | 抓取层（API 直连 → Playwright 拦截 → HAR 回退） |
| `src/mihoyo_toolkit/extractors/` | 提取层（读库 → 导出 TXT） |
| `src/mihoyo_toolkit/exporters/` | Excel / RSS / JSON Feed 导出 |
| `src/mihoyo_toolkit/cli/` | 命令注册器（`@registry.register`）+ 交互菜单 + argparse |
| `src/mihoyo_toolkit/gui/` | PySide6 MVC 界面（models / controllers / workers / pages） |
| `src/mihoyo_toolkit/utils/` | 日志 / HAR / Cookie / 备份 / 迁移 / TXT 过滤 |
| `tests/unit/` | 单元测试（无外部依赖） |
| `tests/integration/` | 集成测试（本地 SQLite / 文件 IO） |
| `tests/e2e/` | 端到端测试（真实网络，默认跳过） |

## 开发规范

### 代码风格

- **Python 3.11+**（`pyproject.toml` 的 `requires-python = ">=3.11"`）
- 使用类型注解，公开函数尽量标注参数与返回值
- 抓取器放 `src/mihoyo_toolkit/scrapers/`，提取器放 `src/mihoyo_toolkit/extractors/`
- 读配置统一走 `mihoyo_toolkit.core.get_settings()`，不要直接解析 `config.toml`
- 落库统一走 `mihoyo_toolkit.core.Storage`，不要自行拼 SQLite 路径
- 新增命令行功能用 `@registry.register(...)` 注册，交互菜单会自动出现
- 耗时逻辑不要放进 GUI 线程：在页面里用 `BasePage.run_task()` 交给 `TaskController`

### 提交前自检（应与 CI 一致，全部通过）

```bash
ruff check .                            # lint
ruff format --check .                   # 格式
mypy --ignore-missing-imports           # 类型
pytest --cov --cov-report=term-missing  # 测试 + 覆盖率
```

覆盖率门槛 **80%**（`gui/` 与 `__main__.py` 按配置不计入）；`gui/` 由
`tests/unit/test_gui_smoke.py` 以 offscreen 方式做冒烟测试。

### 提交信息

使用清晰的提交信息，建议格式：

```
<type>: <简短描述>

<详细说明（可选）>
```

type 可选值：

- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `refactor`: 重构
- `build`: 构建 / CI
- `chore`: 杂项

## 测试

分层标记（`unit` / `integration` / `e2e`）由 `tests/conftest.py` **按目录自动添加**，
因此放进对应目录即可，无需手写 `pytestmark`：

```bash
pytest                          # 全部（e2e 默认跳过）
pytest -m unit                  # 仅单元测试
pytest -m integration           # 仅集成测试
MIHOYO_E2E=1 pytest -m e2e      # 真实网络端到端（需联网）
```

新增功能请同时补充对应层级的测试：纯逻辑放 `tests/unit/`，涉及 SQLite / 文件读写或
子进程的放 `tests/integration/`，需要真实网络的放 `tests/e2e/`。真实网络用例也可在
Actions 页面手动触发 `E2E (manual)` workflow（不会随 push 自动运行）。

## 提交 PR

1. 从 `main` 创建功能分支：`git checkout -b feature/xxx`
2. 提交变更：`git commit -m "feat: xxx"`
3. 推送分支：`git push origin feature/xxx`（分支推送不会触发 CI）
4. 向 `main` 创建 Pull Request —— PR 会运行 lint / test / type

## 安全注意

- **不要**提交包含 Cookie、Token 等敏感信息的文件
- `config.toml` 可能含账号相关配置，提交前确认无敏感内容
- `har/` 目录（可能含 Cookie / Session）已在 `.gitignore` 中，请勿手动添加
- `data/`、`logs/`、`output/` 均为运行期产物，已在 `.gitignore` 中

## 问题反馈

- Bug 报告：使用 [Bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.yml)
- 功能建议：使用 [功能建议模板](.github/ISSUE_TEMPLATE/feature_request.yml)
