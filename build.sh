#!/usr/bin/env bash
# miHoYo ToolKit Build Script v1.0.0 (Linux/macOS)
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Detect Python
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
  miHoYo ToolKit Build Script v1.0.0
============================================================

  Usage: ./build.sh <command>

  Commands:
    deps           Install dependencies (incl. PyInstaller)
    test           Run unit tests
    exe            Build EXE (onefile, Windows only)
    exe-onefile    Build single-file EXE (Windows only)
    exe-onedir     Build directory mode (Windows only)
    docker         Build Docker image
    clean          Clean temp files (type YES to confirm)
    all            Run deps + test
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
        "$PIP" install -r requirements.txt
        "$PIP" install pyinstaller
        echo "[OK] Dependencies installed"
        ;;
    test)
        echo "[INFO] Running unit tests..."
        "$PYTHON" -m unittest discover -s tests -v
        echo "[OK] All tests passed"
        ;;
    exe|exe-onefile|exe-onedir)
        echo "[ERROR] EXE build is Windows-only. Use build.ps1 on Windows."
        exit 1
        ;;
    docker)
        echo "[INFO] Building Docker image..."
        docker build -t mihoyo-toolkit:1.0.0 -t mihoyo-toolkit:latest .
        echo "[OK] Docker image built: mihoyo-toolkit:1.0.0"
        ;;
    clean)
        echo "[INFO] Will clean:"
        echo "  - __pycache__ dirs and *.pyc files"
        echo "  - logs/*.log files"
        echo "  - build/ and dist/ temp dirs"
        echo "  - .pytest_cache"
        echo ""
        read -r -p "Confirm? Type YES to continue: " CONFIRM
        if [ "$CONFIRM" != "YES" ]; then
            echo "[INFO] Clean cancelled"
            exit 0
        fi
        echo ""
        echo "[INFO] Cleaning..."
        find . -path ./.venv -prune -o -path ./.git -prune -o \
            -name "__pycache__" -type d -print -exec rm -rf {} + 2>/dev/null
        find . -path ./.venv -prune -o -path ./.git -prune -o \
            -name "*.pyc" -type f -print -exec rm -f {} + 2>/dev/null
        rm -f logs/*.log 2>/dev/null
        rm -rf build dist .pytest_cache 2>/dev/null
        echo ""
        echo "[OK] Clean complete"
        ;;
    all)
        "$0" deps
        "$0" test
        ;;
    *)
        echo "[ERROR] Unknown command: $CMD"
        echo ""
        show_help
        exit 1
        ;;
esac
