# 贡献指南

感谢你对米游社工具箱的关注！以下是参与贡献的指南。

## 开发环境搭建

```bash
# 1. Fork 并克隆
git clone https://github.com/vers123/mihoyo-tool-kit.git
cd mihoyo-tool-kit

# 2. 虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt
playwright install chromium
```

## 开发规范

### 代码风格

- Python 3.8+ 兼容
- 使用类型注解（type hints）
- 模块组织：抓取器在 `fetchers/`，提取器在 `extractors/`
- 遵循现有基类架构（`BaseScraper`、`GameNewsBaseScraper` 等）

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
- `build`: 构建/CI
- `chore`: 杂项

## 测试

```bash
python -m unittest discover -s tests -v
```

新增功能请同时添加对应的单元测试到 `tests/` 目录。

## 提交 PR

1. 创建功能分支：`git checkout -b feature/xxx`
2. 提交变更：`git commit -m "feat: xxx"`
3. 推送分支：`git push origin feature/xxx`
4. 创建 Pull Request

## 安全注意

- **不要**提交包含 Cookie、Token 等敏感信息的文件
- `har/` 目录已在 `.gitignore` 中，请勿手动添加
- `config.json` 如包含敏感数据请勿提交

## 问题反馈

- Bug 报告：使用 [Bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.yml)
- 功能建议：使用 [功能建议模板](.github/ISSUE_TEMPLATE/feature_request.yml)
