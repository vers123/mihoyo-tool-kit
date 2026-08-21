#!/usr/bin/env bash
# =============================================================================
# 米游社工具箱 ZeroTermux 一键安装与环境准备脚本
# 适配版本：ZeroTermux 0.118.3.64（Android aarch64/arm64，兼容普通 Termux）
#
# 本脚本完成的工作：
#   1. 检查/安装 ZeroTermux 宿主侧依赖：python, git, proot-distro, pulseaudio 等
#   2. 选择性安装 proot-distro/ubuntu（推荐容器）或 debian
#   3. 在容器内安装 chromium-browser、Python3、pip、字体（中文）、nss 等 Playwright 依赖库
#   4. 在容器内 pip install playwright（仅需要 Python 绑定，browser binary 用系统 chromium）
#   5. 在 ZeroTermux 宿主侧（当前项目根）安装 requirements.txt（playwright>=1.40.0）
#   6. 写入启动包装脚本 scripts/zt_launcher.sh 与 scripts/zt_enter.sh
#   7. 若已安装存储权限，可选择把数据目录重定向到 /sdcard/Download/miHoYo_ToolKit
#
# 用法：
#   方式一（全量推荐，一步到位）：
#       bash scripts/install_zerotermux.sh all
#
#   方式二（分步骤）：
#       bash scripts/install_zerotermux.sh pkg_host            # 只装宿主侧包
#       bash scripts/install_zerotermux.sh distro_install      # 安装 ubuntu proot-distro
#       bash scripts/install_zerotermux.sh distro_setup        # 进入容器配置依赖
#       bash scripts/install_zerotermux.sh launcher            # 仅生成启动/进入脚本
#       bash scripts/install_zerotermux.sh info                # 打印环境报告
#
#   环境变量（可选）：
#       DISTRO_NAME=debian  # 选 debian（默认 ubuntu）
#       DISTRO_ARCH=arm64   # proot-distro 架构（auto 即自动，aarch64 用 arm64）
#       REUSE_EXISTING=1    # 容器已存在时跳过安装，直接做容器内配置
#       SKIP_SDCARD=1       # 跳过 /sdcard 共享存储设置
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )"

DISTRO_NAME="${DISTRO_NAME:-ubuntu}"
DISTRO_ARCH="${DISTRO_ARCH:-auto}"
REUSE_EXISTING="${REUSE_EXISTING:-0}"
SKIP_SDCARD="${SKIP_SDCARD:-0}"

# =============================================================================
# 彩色输出
# =============================================================================
color() { local code="$1"; shift; printf '\033[%sm%s\033[0m\n' "$code" "$*"; }
info()    { color 32 "[INFO]" "$*"; }
warn()    { color 33 "[WARN]" "$*"; }
error()   { color 31 "[ERROR]" "$*"; }
step()    { color 36 "[STEP]" "$*"; }

require_termux() {
    if [[ -z "${PREFIX:-}" ]] || [[ ! -d "$PREFIX/bin" ]]; then
        error "该脚本必须在 ZeroTermux / Termux Shell 中运行（检测不到 \$PREFIX ）"
        error "请打开 ZeroTermux APP，在命令行中执行：bash scripts/install_zerotermux.sh"
        exit 1
    fi
    case "$(uname -o 2>/dev/null || true)" in
        *Android*) : ;;
        *)
            warn "未检测到 Android 内核（uname -o=$(uname -o 2>/dev/null)），仅用于调试"
            ;;
    esac
}

pkg_host_deps() {
    step "安装 ZeroTermux 宿主侧依赖 (pkg install)"
    pkg update -y -o Dpkg::Options::="--force-confnew" || true
    local deps=(
        python
        python-pip
        git
        proot-distro
        pulseaudio
        openssl
        libandroid-support
        libandroid-glob
        tsu
        termux-tools
    )
    # 部分包名在 ZeroTermux 源上可能叫 "python" 而无单独的 pip
    pkg install -y "${deps[@]}" || true
    # 确保 pip 可用
    if ! command -v pip >/dev/null 2>&1; then
        python3 -m ensurepip --upgrade || true
        python3 -m pip install --upgrade pip setuptools wheel || true
    fi
    info "宿主侧依赖完成：python=$(python3 --version 2>&1 | awk '{print $2}')  pip=$(pip --version 2>&1 | awk '{print $2}')"
}

distro_install() {
    step "proot-distro 安装发行版：${DISTRO_NAME}"
    if proot-distro list 2>/dev/null | grep -q "^${DISTRO_NAME}$"; then
        if [[ "${REUSE_EXISTING}" == "1" ]]; then
            info "检测到已存在的 ${DISTRO_NAME} 容器（REUSE_EXISTING=1），跳过安装"
            return
        fi
        warn "检测到已存在的 ${DISTRO_NAME} 容器。设置 REUSE_EXISTING=1 可跳过此步骤，否则将执行重新安装（可能清空容器内容）"
        read -r -p "输入 y 继续重新安装，其他键取消： " yn
        if [[ "$yn" != "y" && "$yn" != "Y" ]]; then
            info "跳过 proot-distro install"
            return
        fi
    fi
    local arch_opt=()
    if [[ "${DISTRO_ARCH}" != "auto" ]]; then
        arch_opt+=(--arch "${DISTRO_ARCH}")
    fi
    proot-distro install "${arch_opt[@]}" "${DISTRO_NAME}"
    info "proot-distro/${DISTRO_NAME} 安装完成"
}

distro_setup_once() {
    # 在容器内部执行的脚本，作为 heredoc 传给 proot-distro login -- bash -c
    cat <<'PROOT_EOF'
#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "[PROOT-1/6] APT 更新 + 基础工具"
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg locales tzdata sudo file \
    bzip2 xz-utils unzip wget

echo "[PROOT-2/6] 生成 zh_CN.UTF-8 locale"
locale-gen zh_CN.UTF-8 || true
update-locale LANG=zh_CN.UTF-8 || true
echo "Asia/Shanghai" > /etc/timezone || true
dpkg-reconfigure -f noninteractive tzdata || true

echo "[PROOT-3/6] 安装 chromium + 依赖库（Playwright 运行必需）"
# 中文 & emoji 字体：字体必须装否则抓下来 HTML 中文全是豆腐块
apt-get install -y --no-install-recommends \
    chromium chromium-common \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdbus-1-3 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 \
    fonts-noto-cjk fonts-noto-color-emoji \
    python3 python3-pip python3-venv

echo "[PROOT-4/6] 安装 playwright Python 绑定（全局）"
python3 -m pip install --break-system-packages --upgrade pip setuptools wheel || true
python3 -m pip install --break-system-packages 'playwright>=1.40.0' || true

echo "[PROOT-5/6] 校验 chromium 可执行文件"
for bin in /usr/bin/chromium /usr/bin/chromium-browser; do
    if [[ -x "$bin" ]]; then
        echo "[PROOT] 找到 chromium: $bin -> $( $bin --version 2>&1 | head -1 )"
        break
    fi
done

echo "[PROOT-6/6] 准备项目挂载目录：/workspace_mtk 指向宿主项目根"
# proot-distro 默认把宿主 $HOME 挂载到容器 /data/data/.../files/home
# 这里我们通过在 /root/.bashrc 里提供一个别名，不做软连接以免污染
PROJECT_HOME_HOST="${MTK_HOST_PROJECT_ROOT:-}"
if [[ -n "$PROJECT_HOME_HOST" && -d "$PROJECT_HOME_HOST" ]]; then
    echo "export MTK_HOST_PROJECT_ROOT=\"$PROJECT_HOME_HOST\"" >> /root/.bashrc || true
fi
echo "alias mtkcd='cd \"\$MTK_HOST_PROJECT_ROOT\"'" >> /root/.bashrc || true
echo "[PROOT] 容器内配置完成"

PROOT_EOF
}

distro_setup() {
    step "配置 proot 容器内部环境 (chromium/python/fonts)"
    if ! proot-distro list 2>/dev/null | grep -q "^${DISTRO_NAME}$"; then
        error "尚未安装 ${DISTRO_NAME} 容器，先执行 distro_install 或重新运行 bash scripts/install_zerotermux.sh all"
        exit 2
    fi
    local inner_script
    inner_script="$(mktemp "${TMPDIR:-/tmp}/mtk-proot-XXXXXX.sh")"
    distro_setup_once > "$inner_script"
    # 注意：proot-distro login 默认共享 HOME，我们用 root 用户以便 apt 安装
    # 传递宿主项目目录路径作为环境变量（需要经过 -- 后面 shell -c 解析）
    chmod +x "$inner_script"
    proot-distro login --user root "${DISTRO_NAME}" -- \
        env MTK_HOST_PROJECT_ROOT="$PROJECT_ROOT" bash -c "bash $inner_script"
    rm -f "$inner_script"
    info "容器内部环境配置完成"
}

host_install_python_deps() {
    step "ZeroTermux 宿主侧安装项目 Python 依赖 (requirements.txt)"
    cd "$PROJECT_ROOT"
    python3 -m pip install --user --upgrade pip setuptools wheel || true
    # 注意：在 Termux 宿主直接 pip 安装 playwright 可能失败（官方无 aarch64 manylinux wheel）。
    # 项目代码本身支持 MIHOYO_TOOLKIT_CHROMIUM_BIN，只要宿主有 playwright Python 绑定即可；
    # 如果宿主装不上则退而求其次：把 "miHoYo ToolKit 在宿主安装依赖 + 用 launcher 在容器里跑"。
    set +e
    python3 -m pip install --user -r requirements.txt
    local pip_rc=$?
    set -e
    if [[ $pip_rc -ne 0 ]]; then
        warn "宿主侧 pip install 失败（常见于 aarch64 无 wheel）。"
        warn "推荐：使用 scripts/zt_launcher.sh 在 proot-distro 容器中执行 python main.py（已经装好 pip 绑定和 chromium）。"
    else
        info "宿主侧依赖安装完成"
    fi
}

write_launchers() {
    step "生成启动辅助脚本：scripts/zt_enter.sh + scripts/zt_launcher.sh"
    local enter="$PROJECT_ROOT/scripts/zt_enter.sh"
    local launcher="$PROJECT_ROOT/scripts/zt_launcher.sh"

    cat > "$enter" <<'EOF'
#!/usr/bin/env bash
# 快速进入 proot-distro 容器（默认 ubuntu），进入后自动 cd 到项目目录
set -euo pipefail
DISTRO="${DISTRO_NAME:-ubuntu}"
PROJECT_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
echo "[ZT_ENTER] 进入 proot-distro/${DISTRO} 容器"
export MTK_HOST_PROJECT_ROOT="$PROJECT_ROOT"
# 默认把宿主 ~ 映射进容器后，宿主项目路径 = /data/data/com.zerotermux/files/home/... 可在容器里直接访问
# 这里 login 后执行：cd 到项目路径 + bash
proot-distro login --user root "$DISTRO" -- bash -lc "
export MTK_HOST_PROJECT_ROOT=\"$PROJECT_ROOT\"
export PATH=\"/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:\$PATH\"
cd \"$PROJECT_ROOT\" 2>/dev/null || cd ~
bash
"
EOF

    cat > "$launcher" <<'EOF'
#!/usr/bin/env bash
# 在 proot-distro 容器中执行米游社工具箱 main.py，自动把退出码透传回宿主
set -euo pipefail
DISTRO="${DISTRO_NAME:-ubuntu}"
PROJECT_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$PROJECT_ROOT"

# 1. 如果宿主侧 pip 装好了 playwright 且能找到 chromium 直接跑宿主（省一步 proot 进入）
HOST_FAST_PATH_OK=1
python3 -c "import playwright" >/dev/null 2>&1 || HOST_FAST_PATH_OK=0
CHROME_BIN=""
for p in \
    /data/data/com.zerotermux/files/usr/bin/chromium \
    /data/data/com.termux/files/usr/bin/chromium; do
    if [[ -x "$p" ]]; then CHROME_BIN="$p"; break; fi
done
if [[ "${ZT_NO_HOST_FAST:-0}" != "1" ]] && [[ "$HOST_FAST_PATH_OK" == "1" ]] && [[ -n "$CHROME_BIN" ]]; then
    echo "[ZT_LAUNCHER] 使用宿主路径快速启动: python=$CHROME_BIN"
    export MIHOYO_TOOLKIT_CHROMIUM_BIN="$CHROME_BIN"
    exec python3 "$PROJECT_ROOT/main.py" "$@"
fi

# 2. 走 proot-distro
echo "[ZT_LAUNCHER] 启动 proot-distro/${DISTRO} 并执行 main.py（参数：$*）"
proot-distro login --user root "$DISTRO" -- bash -lc "
export MTK_HOST_PROJECT_ROOT=\"$PROJECT_ROOT\"
export PATH=\"/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:\$PATH\"
# 自动发现 chromium 并暴露给 Python 代码
for p in /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome-stable; do
    if [[ -x \"\$p\" ]]; then export MIHOYO_TOOLKIT_CHROMIUM_BIN=\"\$p\"; break; fi
done
cd \"$PROJECT_ROOT\" || { echo '找不到项目目录'; exit 2; }
python3 main.py $*
"
EOF
    chmod +x "$enter" "$launcher"
    info "辅助脚本已生成："
    info "  $enter   — 进入容器交互 shell"
    info "  $launcher — 一条命令在容器中运行 python main.py"
}

sdcard_redirect() {
    if [[ "${SKIP_SDCARD}" == "1" ]]; then
        info "已跳过 sdcard 重定向 (SKIP_SDCARD=1)"
        return
    fi
    step "可选：把数据输出目录重定向到 /sdcard/Download/miHoYo_ToolKit"
    if [[ ! -d /sdcard ]]; then
        warn "未挂载 /sdcard，跳过。请先在 ZeroTermux 中执行 termux-setup-storage 授予文件访问权限后再运行。"
        return
    fi
    read -r -p "是否把 data/html / data/results 等目录改写到 /sdcard/Download/miHoYo_ToolKit? (y/N) " yn
    case "$yn" in
        y|Y) : ;;
        *)   info "已跳过 sdcard 重定向" ; return ;;
    esac
    local target="/sdcard/Download/miHoYo_ToolKit"
    mkdir -p "$target"
    # 写入 config.json 的 zerotermux_settings.data_dir_override
    local cfg="$PROJECT_ROOT/config.json"
    if ! python3 - "$cfg" "$target" <<'PYEOF'
import json, sys
cfg_path, target = sys.argv[1], sys.argv[2]
os_compat = __import__("os")
os_compat.makedirs(target, exist_ok=True)
try:
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    data = {}
zt = data.setdefault("zerotermux_settings", {})
zt["data_dir_override"] = target
# 同时把浏览器启动参数补上 /sdcard 中文路径权限无关的内容
with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[CONFIG] zerotermux_settings.data_dir_override = {target}")
PYEOF
    then
        error "写入 config.json 失败"
        return
    fi
    info "sdcard 重定向已写入 config.json。所有 HTML/结果/备份都会保存到 $target"
}

print_env_info() {
    echo "======================================================"
    echo " 米游社工具箱 ZeroTermux 环境报告"
    echo "======================================================"
    echo "  ZeroTermux APP 版本:     ${ZEROTERMUXTARGET_VERSION:-未知（建议 0.118.3.64）}"
    echo "  Termux \$PREFIX:          ${PREFIX:-N/A}"
    echo "  Termux \$HOME:            ${HOME:-N/A}"
    echo "  架构:                     $(uname -m)"
    echo "  内核:                     $(uname -r)"
    echo "  Python (宿主):            $(python3 --version 2>&1)"
    echo "  pip3 (宿主):              $(command -v pip3 || echo N/A)"
    echo "  proot-distro:             $(command -v proot-distro || echo 未安装)"
    distros=$(proot-distro list 2>/dev/null | tr '\n' ',')
    echo "  已安装 proot 发行版:      ${distros:-(无)}"
    echo "  项目根目录:               $PROJECT_ROOT"
    echo "  Chromium 宿主路径探测:"
    for p in \
        /data/data/com.zerotermux/files/usr/bin/chromium \
        /data/data/com.termux/files/usr/bin/chromium \
        /data/data/com.zerotermux/files/home/.proot-distro/ubuntu/usr/bin/chromium \
        /data/data/com.zerotermux/files/home/.proot-distro/ubuntu/usr/bin/chromium-browser; do
        if [[ -x "$p" ]]; then
            echo "      ✅ $p"
        fi
    done
    echo "======================================================"
    echo " 常用命令："
    echo "   一步启动:    bash $PROJECT_ROOT/scripts/zt_launcher.sh"
    echo "   进入容器:    bash $PROJECT_ROOT/scripts/zt_enter.sh"
    echo "   只在宿主跑:  MIHOYO_TOOLKIT_CHROMIUM_BIN=... python3 main.py"
    echo "======================================================"
}

do_all() {
    require_termux
    pkg_host_deps
    distro_install
    distro_setup
    host_install_python_deps
    write_launchers
    sdcard_redirect
    print_env_info
    info "全部安装完成！🎉 现在可以运行：bash scripts/zt_launcher.sh"
}

cmd="${1:-all}"
case "$cmd" in
    all)             do_all ;;
    pkg_host)        require_termux; pkg_host_deps ;;
    distro_install)  require_termux; distro_install ;;
    distro_setup)    require_termux; distro_setup ;;
    host_pip)        require_termux; host_install_python_deps ;;
    launcher)        write_launchers ;;
    sdcard)          sdcard_redirect ;;
    info)            print_env_info ;;
    -h|--help|help)
        sed -n '2,40p' "${BASH_SOURCE[0]}"
        ;;
    *)
        error "未知命令: $cmd"
        echo "可用命令：all, pkg_host, distro_install, distro_setup, host_pip, launcher, sdcard, info"
        exit 2
        ;;
esac
