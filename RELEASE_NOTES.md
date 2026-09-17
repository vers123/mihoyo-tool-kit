# Release v1.0.0

> 首个正式版 · 2026-09-18

## 🎉 版本亮点

### 新增功能
- **TXT 文件过滤** — 按关键词匹配提取行，支持精准/模糊匹配、预览、按时间降序重编号
- **TXT 过滤预览** — GUI 表格预览匹配结果，确认后输出
- **tqdm 进度条** — 微博、新闻、用户发帖抓取实时进度显示
- **构建系统** — PyInstaller EXE 打包、Docker 双模式、GitHub Actions CI/CD
- **缓存清理** — CLI 菜单 + 构建脚本，带二次确认
- **应用图标** — 多尺寸 ICO，窗口和任务栏显示

### 重要修复
- **微博抓取** — 修复 `bid` 字段缺失（改用 `mblogid`），修复分页逻辑（`since_id` 游标），支持英文日期解析，可抓到 2019 年数据
- **抓取完整性** — 移除所有抓取器的人为上限，依赖 API/滚动终止信号确保抓全
- **GUI 原生风格** — 切换为 PySide6 平台原生样式，移除自定义 QSS

### 其他变更
- 关键词匹配逻辑从 AND 改为 OR
- 版本号从 5.0.0 重置为 1.0.0
- 新增 CHANGELOG.md 版本历史

## 📦 下载

- **Windows EXE**: 见下方 Assets
- **Docker**: `docker pull vers123/mihoyo-toolkit:1.0.0`

## 🚀 快速开始

```bash
# 源码运行
git clone https://github.com/vers123/mihoyo-tool-kit.git
cd mihoyo-tool-kit
pip install -r requirements.txt
playwright install chromium
python main.py              # CLI 模式
python main.py --gui        # GUI 模式
```

## 🔧 构建

```powershell
.\build.ps1 deps
.\build.ps1 exe-onedir      # 打包 EXE
```

## 📄 完整变更

详见 [CHANGELOG.md](CHANGELOG.md)。
