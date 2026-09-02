# 米游社工具箱 Docker 镜像（D1）
#
# 定位：CLI 模式容器，走 API 直连 + SQLite + Excel，无需 playwright/PySide6 GUI。
# 适合定时任务：docker run --rm -v $PWD/data:/app/data mihoyo-toolkit --fetch all --export-excel
#
# 如需交互菜单或浏览器兜底，另装 playwright 并执行 `playwright install chromium`。

FROM python:3.11-slim

WORKDIR /app

# 系统依赖：证书（HTTPS 请求）+ tzdata（时区，日志时间正确）
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

# 先装依赖（利用层缓存）。CLI 模式仅需以下 4 个；
# 完整交互/GUI 能力需额外 playwright + PySide6（见 requirements.txt）
RUN pip install --no-cache-dir \
        httpx>=0.27.0 \
        tenacity>=8.2.0 \
        pydantic>=2.0.0 \
        openpyxl>=3.1.0

# 复制项目代码
COPY . .

# 数据持久化：SQLite 库、Excel 输出、日志
VOLUME ["/app/data", "/app/output", "/app/logs"]

# 默认入口：抓取全部游戏 + 导出 Excel + 显示条数
# 可被 docker run 参数覆盖，如：docker run --rm <img> --count
ENTRYPOINT ["python", "main.py"]
CMD ["--fetch", "all", "--export-excel", "--count"]
