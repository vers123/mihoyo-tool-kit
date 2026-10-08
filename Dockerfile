# 米游社工具箱 Docker 镜像 (v2.0.0)
#
# 两种构建模式（通过 --build-arg MODE 切换）：
#   MODE=cli    （默认）CLI / API 模式，轻量：仅 httpx / tenacity / pydantic /
#                        pydantic-settings / tqdm / openpyxl，不含 Playwright / PySide6。
#   MODE=full   完整模式：含 Playwright + PySide6 系统依赖（GUI 需 X11 转发）。
#
# 构建 CLI 模式：
#   docker build -t mihoyo-toolkit .
#
# 构建完整模式：
#   docker build --build-arg MODE=full -t mihoyo-toolkit:full .
#
# 运行 CLI 模式：
#   docker run --rm -v $PWD/data:/app/data mihoyo-toolkit --fetch all --export-excel
#
# 运行 GUI 模式（Linux，需 X11）：
#   docker run --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v $PWD/data:/app/data mihoyo-toolkit:full --gui
#
# 注意：本项目为 src/ layout，包体位于 /app/src/mihoyo_toolkit，
#       因此必须 `pip install -e .`（推荐）或在运行时设置 PYTHONPATH=/app/src，
#       否则 `mihoyo-toolkit` 入口与 import 均无法解析。

ARG MODE=cli
FROM python:3.11-slim

ARG MODE=cli

WORKDIR /app

# 基础系统依赖（时区 + 证书）
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ---- 完整模式的系统依赖（Playwright + PySide6 运行库）----
RUN if [ "$MODE" = "full" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
            libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
            libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
            libx11-xcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
            libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 \
            libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 \
            libegl1 libgl1 libglib2.0-0 \
            xauth xvfb \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# 复制项目代码（src/ layout：包体在 /app/src/mihoyo_toolkit）
COPY . .

# ---- 安装项目本身 ----
# 关键：src/ layout 不能用 `pip install .` 后直接 `python -m mihoyo_toolkit`
# 读取源码目录，此处统一采用可编辑安装（-e），使 /app/src 进入 sys.path。
#
# cli 模式：`--no-deps -e .` 仅注册包与入口点，随后手动安装轻量运行依赖，
#           避免拉入 playwright（~含驱动）与 PySide6（体积大）等重依赖。
# full 模式：`pip install -e ".[excel,pinyin]"` 安装全部依赖（含 PySide6 / Playwright），
#           再下载 chromium 及其系统依赖。
RUN if [ "$MODE" = "cli" ]; then \
        pip install --no-cache-dir --no-deps -e . \
        && pip install --no-cache-dir \
            "httpx>=0.27.0" \
            "tenacity>=8.2.0" \
            "pydantic>=2.6.0" \
            "pydantic-settings>=2.2.0" \
            "tqdm>=4.65.0" \
            "openpyxl>=3.1.0"; \
    else \
        pip install --no-cache-dir -e ".[excel,pinyin]" \
        && playwright install --with-deps chromium; \
    fi

# 数据持久化
VOLUME ["/app/data", "/app/output", "/app/logs", "/app/har"]

# 默认入口（mihoyo-toolkit 由 [project.scripts] 提供）
ENTRYPOINT ["mihoyo-toolkit"]
CMD ["--fetch", "all", "--export-excel", "--count"]
