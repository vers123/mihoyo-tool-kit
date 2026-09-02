# 米游社工具箱 — 改造计划（基于 RPA 评估）

> 配套文档：[RPA适用性评估.md](file:///workspace/ai-docs/RPA适用性评估.md)
> 制定日期：2026-09-02
> 所在分支：`docs/rpa-evaluation`
> 状态：**v1.0 定稿 — 提问流程已完成**

---

## 一、总体方针

依据评估结论，**不整体迁移至 RPA**，按"保主线 + 可选插件 + 更优替代"三档推进：

| 档位 | 方向 | 优先级 | 适用条件 | 本次结论 |
| --- | --- | --- | --- | --- |
| A 主线优化 | 保留 Playwright，向"直接调 API"演进 | ★★★ 默认推进 | 无强 RPA 需求时 | ✅ **启动**：API 直连 + Playwright 回退双通道 |
| B 易用性增强 | GUI + 定时调度 + 配置可视化 + Excel 落地 | ★★ 推进 | 非技术用户自助 | ✅ **启动**：含 Excel 写入（openpyxl，替代 RPA） |
| C RPA 可选插件 | 仅在人工登录/桌面混合场景局部封装 | ☆ 搁置 | 出现强需求且提问确认后 | ⏸ **搁置**：动机仅为对比评估，无强需求 |

> 提问流程结论：动机=仅作对比评估，故 **C 档搁置**；Excel 写入需求由 Python `openpyxl` 承担，无需 RPA；运行环境为 Windows 个人机，RPA 技术可行但非必要。

---

## 二、A 档：主线优化（推荐，不依赖 RPA）— ✅ 已确认启动

> 提问确认：采用 **API 直连 + Playwright 回退双通道**（A1 + A2 同时落地）。

### A1. 抽取"直接 API 客户端"
- 目标：把 `content_v2_user` 等 API 从"浏览器拦截"升级为"直接 `httpx` 请求"。
- 收益：去掉浏览器启动开销，单次抓取耗时预计下降 5–10 倍；可在无头服务器/容器运行。
- 影响范围：`core/scraper.py`、`fetchers/news/base.py`，新增 `core/api_client.py`。
- 风险：失去浏览器 Cookie 自动注入便利，需自行管理登录态（已有 `utils/cookie_loader.py` 可复用）。

### A2. 保留 Playwright 作为回退
- 当直接 API 失败（签名变更、风控）时，回退到现有 Playwright 拦截模式。
- 即"API 优先 + 浏览器回退"双通道。

### A3. 增量与备份沿用
- 现有 `incremental_settings` / `backup_settings` 配置不动，迁移到新 API 客户端时复用。

---

## 三、B 档：易用性增强（推荐，不依赖 RPA）— ✅ 已确认启动

> 提问确认：运行环境为 Windows 个人机；存在 Excel/WPS 写入需求，**用 Python `openpyxl` 承担，不引入 RPA**。

### B1. 定时调度
- 用 APScheduler 或系统 cron（Windows 任务计划程序）实现每日增量抓取，无需人工启动。
- 在 `config.json` 新增 `schedule` 段。

### B2. GUI 配置可视化
- 现有 `gui/pages/system.py` 已支持配置编辑，可扩展为表单式配置 + 一键调度。

### B3. 运行报告
- 每次抓取产出 Markdown/JSON 运行报告（新增条数、失败原因、备份位置）。

### B4. Excel 落地（替代 RPA 桌面写入）
- 用 `openpyxl` 直接把抓取结果写入 `.xlsx`，支持三游戏分 sheet、增量追加、样式美化。
- 在 `config.json` 新增 `output_dirs.excel` 与 `filenames.excel_*` 配置。
- 影响范围：新增 `extractors/excel_writer.py`，在 `extractors/__init__.py` 暴露 `run_export_excel()`，GUI `other.py` 增加入口。
- **明确不做**：不调用 Excel COM 自动化、不引入 RPA 操作 WPS/Excel 桌面端。

---

## 四、C 档：RPA 可选插件 — ⏸ 已搁置（本次不启动）

> 提问流程结论：动机仅为"对比评估"，且 Excel 写入已由 B4 用 `openpyxl` 解决，C 档触发条件未达成，本次搁置。仅在未来出现"必须人工过验证码"或"必须操作无 API 的桌面 ERP"时再重启评估。

### 触发条件（任一满足才启动）
- 决策者明确要求接入某 RPA 产品；
- 出现必须人工过验证码/滑块的登录场景；
- 需要把抓取结果写入无 API 的桌面软件。

### C1. 边界封装
- RPA 只封装"人工登录态获取"或"桌面写入"子流程，输出一个 Cookie/Token 文件或落地数据文件。
- 主线 Python 抓取逻辑通过读取该文件继续工作，**不反向依赖 RPA**。

### C2. 候选产品（待确认）
- 影刀 RPA（国产、中文友好、个人版免费）
- 阿里云 RPA（企业级）
- UiPath / Power Automate（国际化场景）

### C3. 不做项
- 不用 RPA 重写新闻抓取主流程；
- 不用 RPA 替换 PySide6 GUI；
- 不用 RPA 替换备份/迁移逻辑。

---

## 五、实施步骤（已定稿）

1. ~~**提问流程**~~：✅ 已完成（见 [第六节](#六待确认清单与提问流程结果)）。
2. ~~**定稿方针**~~：✅ 已定稿 — A 档 + B 档启动，C 档搁置。
3. **A 档落地**（启动）：
   - 新建 `feature/api-client` 分支；
   - 实现 `core/api_client.py`，对三游戏 `content_v2_user` API 做直接请求；
   - 保留 Playwright 回退（双通道）；
   - 在 `tests/` 增补 API 客户端单元测试。
4. **B 档落地**（启动）：
   - B1 调度：`config.json` 新增 `schedule` 段 + APScheduler；
   - B3 运行报告：新增 `utils/report.py`；
   - **B4 Excel 落地**：新增 `extractors/excel_writer.py` + `openpyxl` 依赖，GUI 增加入口。
5. ~~**C 档落地**~~：⏸ 搁置，不建 `rpa/` 目录。
6. **合并与发布**：评估文档与计划文档先合并回 main，代码改造按 feature 分支独立 PR。

---

## 六、待确认清单与提问流程结果

> ✅ 提问流程已于 2026-09-02 完成，决策者回答如下。Q5–Q7 因 Q1 结论（仅作对比评估）而无需继续追问。

| 编号 | 待确认项 | 决策者回答 | 影响 / 落地 |
| --- | --- | --- | --- |
| Q1 | 引入 RPA 的真实动机 | **仅作对比评估** | C 档搁置，不引入 RPA |
| Q2 | 是否允许去掉浏览器直接调 API | **两者都要（直连+回退）** | A 档双通道启动 |
| Q3 | 是否有桌面端混合需求 | **有，需写 Excel/WPS** | B4 用 `openpyxl` 解决，不走 RPA |
| Q4 | 目标运行环境 | **Windows 个人机** | RPA 技术可行但非必要；Python 方案可直接部署 |
| Q5 | 目标 RPA 产品 | —（C 档搁置，未追问） | 不适用 |
| Q6 | 是否存在必须人工处理的登录验证 | —（C 档搁置，未追问） | 不适用 |
| Q7 | 是否接受商业 RPA 授权费用 | —（C 档搁置，未追问） | 不适用 |

_本表已填入答案，计划文档升版至 v1.0 定稿。_
