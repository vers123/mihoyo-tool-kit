# 路径 / 临时文件 / 权限约定

本文说明工具运行时的**可写区域**、**只读区域**与**外部文件处理流程**，是
`core/paths.py`、`core/temp.py`、`utils/fsio.py` 三个模块的行为契约。

## 一、可写区域（仅此三处）

| 区域 | 默认位置 | 说明 |
|---|---|---|
| 工作区根 | 源码运行=仓库根；冻结运行=exe 目录 | `data/`、`logs/`、`har/`、`output/`、`config.toml` 都在这里 |
| 临时根 | 系统 Temp（`tempfile.gettempdir()`） | 本项目所有临时文件都落这里的 `mihoyo-toolkit-*` 随机子目录，用完即删 |
| 用户数据目录 | Windows `%LOCALAPPDATA%\mihoyo-toolkit`；macOS `~/Library/Application Support/mihoyo-toolkit`；其它 `$XDG_DATA_HOME|~/.local/share`/mihoyo-toolkit | **仅当自动探测到的根不可写**（如安装在 `Program Files`）时启用 |

除此之外的任何路径，`utils.fsio.ensure_writable_location()` 都会抛
`StorageError`（提示「工作区外只读：请先复制到工作区或临时目录后再写入」）。

## 二、只读区域（只读不写）

- 工作区之外的任意路径（其它项目、系统目录、用户文档等）；
- Firefox 配置目录（只读取 `cookies.sqlite`，且是**先复制到临时区再打开**）；
- Playwright 浏览器安装目录（`playwright install` 写入，工具本身不修改）；
- `resources/`（字体 / 图标等版本化资源）。

需要使用时：**先复制到工作区或临时目录**，再在副本上操作。

## 三、环境变量优先级

| 变量 | 作用 | 优先级 |
|---|---|---|
| `MIHOYO_HOME` | 覆盖工作区根 | 最高；显式设置但不可写时启动即报 `ConfigError`，不会静默搬家 |
| `MIHOYO_DATA_DIR` | 只覆盖数据目录（`data/`） | 高于工作区根的 `data/` |
| `MIHOYO_TEMP_DIR` | 覆盖临时根 | 高于系统 Temp；不可写时报 `TempError`，不会退回仓库 |
| `MIHOYO_LEGACY_DIR` | v1 旧数据目录（迁移源） | 只读复制，不修改源 |

## 四、写入规则

1. 一律通过 `utils.fsio` 的 `atomic_write_text` / `atomic_write_bytes` / `atomic_save`：
   同目录临时文件 → `os.replace`，中途失败不破坏原文件。
2. 文本一律 UTF-8 + `\n`（显式 `newline="\n"`），产物不随平台变化。
3. 下载类写入先落 `*.part`，完整后再替换；失败清理分片。
4. 临时文件统一走 `core.temp.temp_workspace()`，异常路径同样清理；
   进程被强杀残留的目录由下次启动的 `sweep_stale_temp()`（>24h）兜底。

## 五、权限与审计

- Windows 工作区根会有一条 `Everyone: DeleteSubdirectoriesAndFiles` 的**拒绝**项，
  这是 Windows 沙箱写入的预期保护项，**不要手工删除**。
- 随时可运行只读审计：

```bash
python scripts/workspace_audit.py          # 文本报告
python scripts/workspace_audit.py --json   # 供回归对比
```

审计内容：ACL 拒绝项（区分预期/需关注）、每个运行时目录的
create/write/read/delete 探针、只读属性文件、系统 Temp 下的本项目残留、
可重建缓存体积。退出码非零表示存在真实失败项。
