#!/usr/bin/env bash
# 米游社工具箱 (miHoYo ToolKit) 构建脚本 (Linux/macOS)
# 版本号从 version_info.txt 解析（单一数据源），失败回退 pyproject.toml。
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ---- 版本号 ----
VERSION="$(grep -oE "ProductVersion', u'[0-9]+\.[0-9]+\.[0-9]+" version_info.txt 2>/dev/null | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" | head -1 || true)"
if [ -z "$VERSION" ]; then
    VERSION="$(grep -oE '^version = "[^"]+"' pyproject.toml 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
fi
VERSION="${VERSION:-0.0.0}"

# ---- Python 探测（优先 .venv）----
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
    echo "[INFO] Using venv: .venv"
else
    PYTHON="python3"
    PIP="pip3"
    echo "[INFO] Using system Python"
fi

CMD="${1:-help}"

show_help() {
    cat <<EOF
============================================================
  米游社工具箱 Build Script v$VERSION
============================================================

  Usage: ./build.sh <command>

  Commands:
    deps           Install dependencies + Playwright chromium
    test           Run pytest with coverage
    lint           Run ruff check + ruff format --check
    type           Run mypy type check
    exe            Build EXE (onefile, Windows only)
    exe-onefile    Build single-file EXE (Windows only)
    exe-onedir     Build directory mode (Windows only)
    docker         Build Docker image
    clean          Clean temp files (type YES to confirm)
    all            Run deps + lint + type + test
    help           Show this help

  Examples:
    ./build.sh deps
    ./build.sh docker
    ./build.sh clean
EOF
}

case "$CMD" in
    help|-h|--help)
        show_help
        ;;
    deps)
        echo "[INFO] Installing dependencies..."
        "$PIP" install -e ".[dev,pinyin,excel,icon]"
        "$PYTHON" -m playwright install chromium
        echo "[OK] Dependencies installed"
        ;;
    test)
        echo "[INFO] Running tests with coverage..."
        "$PYTHON" -m pytest --cov --cov-report=term-missing
        echo "[OK] All tests passed"
        ;;
    lint)
        echo "[INFO] Running ruff check..."
        "$PYTHON" -m ruff check .
        echo "[INFO] Running ruff format --check..."
        "$PYTHON" -m ruff format --check .
        echo "[OK] Lint check passed"
        ;;
    type)
        echo "[INFO] Running mypy..."
        "$PYTHON" -m mypy
        echo "[OK] Type check passed"
        ;;
    exe|exe-onefile|exe-onedir)
        echo "[ERROR] EXE build is Windows-only. Use build.ps1 on Windows."
        exit 1
        ;;
    docker)
        echo "[INFO] Building Docker image..."
        docker build -t mihoyo-toolkit:$VERSION -t mihoyo-toolkit:latest .
        echo "[OK] Docker image built: mihoyo-toolkit:$VERSION"
        ;;
    clean)
        echo "[INFO] Will clean:"
        echo "  - __pycache__ dirs and *.pyc / *.pyo files"
        echo "  - logs/*.log files"
        echo "  - build/ and dist/ temp dirs"
        echo "  - .pytest_cache / .ruff_cache / .mypy_cache"
        echo "  - .coverage / htmlcov"
        echo "  (skips .venv / .git / browser / data / har / resources)"
        echo ""
        read -r -p "Confirm? Type YES to continue: " CONFIRM
        if [ "$CONFIRM" != "YES" ]; then
            echo "[INFO] Clean cancelled"
            exit 0
        fi
        echo ""
        echo "[INFO] Cleaning..."
        find . \( -name ".venv" -o -name ".git" -o -name "browser" -o -name "data" \
            -o -name "har" -o -name "resources" \) -prune -o \
            -name "__pycache__" -type d -print -exec rm -rf {} + 2>/dev/null || true
        find . \( -name ".venv" -o -name ".git" -o -name "browser" -o -name "data" \
            -o -name "har" -o -name "resources" \) -prune -o \
            \( -name "*.pyc" -o -name "*.pyo" \) -type f -print -exec rm -f {} + 2>/dev/null || true
        rm -f logs/*.log 2>/dev/null || true
        rm -rf build dist .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage 2>/dev/null || true
        echo ""
        echo "[OK] Clean complete"
        ;;
    all)
        "$0" deps
        "$0" lint
        "$0" type
        "$0" test
        ;;
    *)
        echo "[ERROR] Unknown command: $CMD"
        echo ""
        show_help
        exit 1
        ;;
esac
