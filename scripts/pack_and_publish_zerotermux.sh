#!/usr/bin/env bash
# =============================================================================
# 米游社工具箱 · ZeroTermux 一键打包 + 多落点分发脚本
#
# 作用：
#   1. 以当前项目根为基准 tar.gz 打包（保留 .git 分支历史，排除运行时大目录）
#   2. 必写一份到  ${PROJECT_DIR}/dist/  —— ZeroTermux APP 自己的私有目录，
#      用 ZeroTermux 自带的"文件"或系统文件管理器进入 ZeroTermux 的 home/
#      项目目录/ dist/ 一定能看到，零权限依赖。
#   3. 额外尝试写入 4 个"手机端文件管理器大概率能看到"的共享存储目录：
#        A) /sdcard/LingLan/material/github/Vers123/
#        B) /storage/emulated/0/LingLan/material/github/Vers123/
#        C) /sdcard/Download/miHoYo_ToolKit_bak/
#        D) /storage/emulated/0/Download/miHoYo_ToolKit_bak/
#      共享存储写入前会检测是否真的挂了 Android 共享卷，挂了才写。
#
# 用法（在 ZeroTermux APP 真机 shell 里执行）：
#   cd ~/miHoYo_ToolKit
#   bash scripts/pack_and_publish_zerotermux.sh
#
# 可选环境变量：
#   PROJECT_DIR    覆盖项目根（默认自动定位脚本所在目录的父目录）
#   DIST_SUBDIR    私有目录子路径，默认 "dist"
#   FORCE_PUBLIC=1 即便没检测到共享存储也强制写共享存储路径（会报错给你看）
#   SKIP_PUBLIC=1  完全跳过共享存储写入，只落 dist
# =============================================================================

set -u

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR_DEFAULT="$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_DIR_DEFAULT}"
DIST_SUBDIR="${DIST_SUBDIR:-dist}"

# ---------- 工具函数 ----------
color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
info()  { color 32 "[INFO]  $*"; }
warn()  { color 33 "[WARN]  $*"; }
err()   { color 31 "[ERROR] $*"; }
ok()    { color 36 "[OK]    $*"; }

human_size() {
  local p="$1" sz=0
  sz=$(stat -c %s "$p" 2>/dev/null || stat -f %z "$p" 2>/dev/null || echo 0)
  if [ "$sz" -ge 1073741824 ]; then awk -v s="$sz" 'BEGIN{printf "%.2f GB", s/1073741824}'; return; fi
  if [ "$sz" -ge 1048576 ];    then awk -v s="$sz" 'BEGIN{printf "%.2f MB", s/1048576}';    return; fi
  if [ "$sz" -ge 1024 ];       then awk -v s="$sz" 'BEGIN{printf "%.2f KB", s/1024}';       return; fi
  echo "${sz} B"
}

is_real_android_storage() {
  # 真实挂了共享存储的 3 条快速判据（命中越多越可信），至少满足 2 条算真实
  local score=0
  local root="${1:-/storage/emulated/0}"
  [ -d "$root/Android" ]        && score=$((score+1))
  [ -d "$root/Download" ]       && score=$((score+1))
  [ -d "$root/DCIM" ]           && score=$((score+1))
  # 能创建一个小文件并立刻读到（排除沙箱空目录）
  local probe="$root/.mtk_probe_$$.tmp"
  if echo "$(date +%s)" > "$probe" 2>/dev/null && [ -s "$probe" ]; then
    score=$((score+2))
    rm -f "$probe" 2>/dev/null
  fi
  [ "$score" -ge 3 ] && return 0
  return 1
}

verify_tar() {
  local f="$1"
  [ -f "$f" ] || return 2
  if tar -tzf "$f" >/dev/null 2>&1; then
    # 至少 10 个成员才算"合理内容"
    local members
    members=$(tar -tzf "$f" 2>/dev/null | wc -l)
    [ "$members" -ge 10 ] && return 0
  fi
  return 1
}

# ---------- 目录/项目校验 ----------
cd "$PROJECT_DIR" || { err "无法进入项目目录: $PROJECT_DIR"; exit 2; }

echo "============================================================"
echo "  米游社工具箱 · 打包 + 多落点分发（ZeroTermux 真机版）"
echo "============================================================"
info  "项目根目录       : $PROJECT_DIR"
info  "ZeroTermux \$HOME : ${HOME:-unset}"
info  "PREFIX            : ${PREFIX:-unset}"

if [ ! -d "$PROJECT_DIR/.git" ]; then
  warn "项目下没有 .git 目录，将跳过分支历史打包（仍打包源码）"
  INCLUDE_GIT=0
else
  INCLUDE_GIT=1
  info "Git 分支: $(git --no-pager branch --list --format='%(refname:short)' | tr '\n' ' ')"
fi

# ---------- 1. 打包 ----------
TS="$(date +%Y%m%d-%H%M%S)"
TMP_TAR="/tmp/miHoYo_ToolKit-${TS}.tar.gz"

EXCLUDE_ARGS=(
  --exclude='data/html/*'
  --exclude='data/images/*'
  --exclude='data/results/*'
  --exclude='data/backups/*'
  --exclude='har/*'
  --exclude='logs/*'
  --exclude='__pycache__'
  --exclude='*/__pycache__'
  --exclude='*.pyc'
  --exclude='.venv'
  --exclude='node_modules'
)

echo ""
echo "[1/5] 打包临时 tar.gz -> $TMP_TAR"
# 用 --ignore-failed-read 做容错（避免某个 root owned 目录把整次打包卡死）
if ! tar --ignore-failed-read -czf "$TMP_TAR" "${EXCLUDE_ARGS[@]}" . ; then
  err "tar 命令返回非 0。再尝试一次：去掉 .git 中可能不可读的打包对象（refs/objects 等）"
  tar --ignore-failed-read -czf "$TMP_TAR" "${EXCLUDE_ARGS[@]}" \
      --exclude='.git/objects/*' \
      --exclude='.git/logs/*' \
      .
fi

if [ ! -f "$TMP_TAR" ]; then
  err "打包失败：临时文件没生成 $TMP_TAR"
  exit 3
fi
if ! verify_tar "$TMP_TAR"; then
  err "打包失败：tar 包完整性校验不通过（文件数量不足或 gzip 损坏）"
  exit 3
fi
ok "临时包生成成功，大小 = $(human_size "$TMP_TAR")，成员数 = $(tar -tzf "$TMP_TAR" | wc -l)"

# ---------- 2. 写入必落点：项目私有 dist/ ----------
DIST_DIR="$PROJECT_DIR/$DIST_SUBDIR"
mkdir -p "$DIST_DIR" || { err "mkdir -p $DIST_DIR 失败（无法写入项目目录）"; exit 4; }
PRIVATE_PATH="$DIST_DIR/miHoYo_ToolKit-${TS}.tar.gz"
echo ""
echo "[2/5] 写入必落点（ZeroTermux APP 文件里 100% 可见）: $PRIVATE_PATH"
cp -f "$TMP_TAR" "$PRIVATE_PATH"
if ! verify_tar "$PRIVATE_PATH"; then
  err "拷贝到 dist/ 后完整性校验失败！"
  exit 5
fi
ok "✓ dist/ 落点成功：大小 $(human_size "$PRIVATE_PATH")"

# ---------- 3. 共享存储可到达性判定 ----------
PUBLIC_OK=0
PUBLIC_ROOTS=()
if [ "${SKIP_PUBLIC:-0}" = "1" ]; then
  warn "SKIP_PUBLIC=1：跳过所有共享存储写入"
elif [ "${FORCE_PUBLIC:-0}" = "1" ]; then
  info "FORCE_PUBLIC=1：强制尝试写共享存储（即便判定失败）"
  PUBLIC_OK=1
  PUBLIC_ROOTS=(/sdcard /storage/emulated/0)
else
  for root in /sdcard /storage/emulated/0; do
    if [ -d "$root" ] && is_real_android_storage "$root"; then
      PUBLIC_OK=1
      PUBLIC_ROOTS+=("$root")
    fi
  done
fi

echo ""
echo "[3/5] 共享存储判定：PUBLIC_OK=$PUBLIC_OK  有效根目录：${PUBLIC_ROOTS[*]:-无}"

# ---------- 4. 写共享存储（4 条候选路径） ----------
declare -a PUBLISHED_PATHS=()
declare -a FAILED_PATHS=()

publish_one() {
  local dest_dir="$1" fallback="${2:-}"
  mkdir -p "$dest_dir" 2>/dev/null || {
    [ -n "$fallback" ] || FAILED_PATHS+=("$dest_dir (mkdir 失败)")
    return 1
  }
  local dest="$dest_dir/miHoYo_ToolKit-${TS}.tar.gz"
  if cp -f "$TMP_TAR" "$dest" 2>/dev/null && verify_tar "$dest"; then
    PUBLISHED_PATHS+=("$dest")
    ok "✓ 手机共享存储成功写入：$dest   ($(human_size "$dest"))"
    return 0
  fi
  FAILED_PATHS+=("$dest")
  return 1
}

echo ""
echo "[4/5] 分发到手机可见目录……"
PUBLISHED_PATHS+=("$PRIVATE_PATH")   # 必落点先算一个
for root in "${PUBLIC_ROOTS[@]:-}"; do
  [ -z "$root" ] && continue
  # A/B: 用户原始需求的精准路径 LingLan/material/github/Vers123
  publish_one "$root/LingLan/material/github/Vers123"
  # C/D: 兜底：Download/miHoYo_ToolKit_bak
  publish_one "$root/Download/miHoYo_ToolKit_bak" 1
done

# ---------- 5. 媒体扫描 + Toast（ZeroTermux 真机才有这俩命令） ----------
echo ""
echo "[5/5] 通知系统扫描 + 通知……"
if command -v termux-media-scan >/dev/null 2>&1; then
  for f in "${PUBLISHED_PATHS[@]}"; do
    termux-media-scan "$f" >/dev/null 2>&1 || true
  done
fi
if command -v termux-toast >/dev/null 2>&1; then
  N=$((${#PUBLISHED_PATHS[@]} - 1))   # 去掉必落点
  termux-toast "打包已完成：共享目录 $N 处 / dist 必落点 1 处" >/dev/null 2>&1 || true
fi

# ---------- 最终汇总 ----------
echo ""
echo "============================================================"
echo " 打包完成汇总（在 ZeroTermux 文件管理器里一定能找到至少 1 份）："
echo "============================================================"
i=0
for f in "${PUBLISHED_PATHS[@]}"; do
  i=$((i+1))
  if [ "$f" = "$PRIVATE_PATH" ]; then tag="（必落点 · APP私有目录 · 100%可见）"
  else tag="（共享存储 · 手机文件管理器可见）"; fi
  echo "  [$i] $f  —  $(human_size "$f")  $tag"
done
echo ""
if [ "${#FAILED_PATHS[@]}" -gt 0 ]; then
  warn "以下路径写入失败（可忽略，上面 $i 份成功已经够用）："
  for f in "${FAILED_PATHS[@]}"; do
    echo "    · $f"
  done
  echo ""
  echo "👉 如果想让 LingLan/material/github/Vers123 这份也成功，解决步骤："
  echo "   1) 在 ZeroTermux 执行：termux-setup-storage  然后点击弹窗『允许』"
  echo "   2) Android 11+/12+/13+：系统设置 → 应用 → ZeroTermux → 权限 → 文件 → 『允许管理所有文件』"
  echo "   3) 再运行一次：bash scripts/pack_and_publish_zerotermux.sh"
fi
echo ""
echo "👉 解压命令：tar -xzf <上面任意一个路径> -C <目标解压目录>"
echo "============================================================"
