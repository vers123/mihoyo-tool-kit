# 米游社工具箱 Docker 镜像
#
# 两种构建模式（通过 build-arg MODE 切换）：
#   MODE=cli    （默认）CLI/API 模式，轻量，无需 playwright/PySide6
#   MODE=full   完整模式，含 Playwright + PySide6（需 X11 转发才能用 GUI）
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

ARG MODE=cli
FROM python:3.11-slim

ARG MODE=cli

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

# ---- CLI 模式依赖（默认）----
RUN if [ "$MODE" = "cli" ]; then \
        pip install --no-cache-dir \
            httpx>=0.27.0 \
            tenacity>=8.2.0 \
            pydantic>=2.0.0 \
            openpyxl>=3.1.0 \
            tqdm>=4.65.0; \
    fi

# ---- 完整模式依赖（含 Playwright + PySide6）----
RUN if [ "$MODE" = "full" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
            libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
            libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
            libx11-xcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
            libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 \
            libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 \
            xauth xvfb \
        && rm -rf /var/lib/apt/lists/* \
        && pip install --no-cache-dir -r requirements.txt \
        && playwright install chromium; \
    fi

# 复制项目代码
COPY . .

# 数据持久化
VOLUME ["/app/data", "/app/output", "/app/logs", "/app/har"]

# 默认入口
ENTRYPOINT ["python", "main.py"]
CMD ["--fetch", "all", "--export-excel", "--count"]
