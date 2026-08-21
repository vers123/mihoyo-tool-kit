#!/usr/bin/env bash
# =============================================================================
#  米游社工具箱 · 安全推送到 GitHub 脚本
#  设计目标：
#    1) 仅需 3 项输入：GH_USERNAME / GH_REPO_NAME / GH_PAT(classic, repo scope)
#    2) 推送前先 --dry-run；推送完成立刻清除 token（insteadOf 解除 + unset + remote 置纯URL）
#    3) 输出每一步退出码，失败立刻停（set -e 除了显式允许的命令）
#    4) 同时推送 main / docs/project-introduction / refactor/zerotermux-adapter 三个分支
#    5) 同时兼容：Trae APP 沙箱（有 HTTPS_PROXY 即可） / ZeroTermux / macOS / Linux
#
#  用法 1（环境变量一次性注入）：
#    GH_USERNAME=LingLanGithub \
#    GH_REPO_NAME=mihoyo-tool-kit \
#    GH_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
#    bash scripts/safe_github_push.sh
#
#  用法 2（交互输入）：
#    bash scripts/safe_github_push.sh
# =============================================================================
set -u
set -o pipefail

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )"
cd "$PROJECT_DIR" || { echo "[FATAL] 无法进入项目目录: $PROJECT_DIR"; exit 2; }

# ---------- 工具 ----------
color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
info()  { color 32 "[INFO]  $*"; }
warn()  { color 33 "[WARN]  $*"; }
err()   { color 31 "[ERROR] $*"; }
ok()    { color 36 "[OK]    $*"; }

die() { err "$*"; cleanup_token; exit 1; }

INSTEADOF_KEY=""       # 被 install_insteadof 设置后，cleanup_token 会 unset 它
INSTEADOF_VALUE_RE=""  # 匹配用的 token 片段，避免卸载时正则写错

install_insteadof() {
    # 把 https://github.com/ 的所有请求都走 token 前缀 insteadOf
    local pat="$1"
    INSTEADOF_KEY="https://x-access-token:${pat}@github.com/"
    git config --global --add url."${INSTEADOF_KEY}".insteadOf "https://github.com/" \
        || die "git config --global insteadOf 写入失败"
    INSTEADOF_VALUE_RE="$pat"
}

cleanup_token() {
    # 1) 清 insteadOf（精确匹配，防止误删其他 git 配置）
    if [ -n "$INSTEADOF_KEY" ]; then
        git config --global --unset-all url."${INSTEADOF_KEY}".insteadOf 2>/dev/null || true
        INSTEADOF_KEY=""
    fi
    # 2) 保险：卸载任何残留的 x-access-token insteadOf（含 ghp_ 字符串）
    if [ -n "$INSTEADOF_VALUE_RE" ]; then
        git config --global --get-regexp '^url\..*x-access-token:.*\.insteadof$' 2>/dev/null \
        | grep -F "$INSTEADOF_VALUE_RE" \
        | while IFS= read -r line; do
            key="${line%% *}"
            git config --global --unset "$key" 2>/dev/null || true
        done
    fi
    # 3) 再保险：检查 .git/config remote URL 里有没有 token，有则立刻替换为纯 URL
    local cur_url
    cur_url="$(git remote get-url origin 2>/dev/null || true)"
    if [[ "$cur_url" == *"x-access-token:"* ]] || [[ "$cur_url" == *"ghp_"* ]]; then
        local stripped
        stripped="$(sed -E 's#https://[^/]*:ghp_[A-Za-z0-9]+@#https://#' <<<"$cur_url" | \
                   sed -E 's#https://x-access-token:[^@]+@#https://#')"
        warn "origin URL 含 token 残留，已自动还原为纯 URL: $stripped"
        git remote set-url origin "$stripped" 2>/dev/null || true
    fi
    # 4) 清 shell 变量（防止 core dump / history 泄漏）
    if [ -n "${GH_PAT:-}" ]; then
        # 用无意义覆盖 + unset
        GH_PAT="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        unset GH_PAT
    fi
}
trap cleanup_token EXIT

# ---------- 采集参数 ----------
if [ -z "${GH_USERNAME:-}" ]; then
    read -r -p "GitHub 用户名（owner，非邮箱）: " GH_USERNAME
fi
if [ -z "${GH_REPO_NAME:-}" ]; then
    read -r -p "GitHub 仓库名（需要先在网页 Create repository 建好、空仓库，不勾选 README/ignore/license）: " GH_REPO_NAME
fi
if [ -z "${GH_PAT:-}" ]; then
    read -r -s -p "Personal Access Token(Classic，勾选 repo 范围，ghp_ 开头 40 字符，输入不会显示): " GH_PAT
    echo ""
fi

# 严格校验
[[ "$GH_USERNAME" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,38}[A-Za-z0-9])?$ ]] \
    || die "GitHub 用户名格式不合法（1~39 位，字母数字-，首尾不能是 -）"
[[ "$GH_REPO_NAME" =~ ^[A-Za-z0-9._-]{1,100}$ ]] \
    || die "仓库名格式不合法（1~100 位，字母数字._-）"
if [[ ! "$GH_PAT" =~ ^ghp_[A-Za-z0-9]{36}$ ]]; then
    # 允许新版 ghp_ 后面是 36~255 位也接受（GitHub 未来可能变长度）
    [[ "$GH_PAT" =~ ^ghp_[A-Za-z0-9]{36,255}$ ]] || die "PAT 必须是 ghp_ 开头的经典 Token"
fi

REPO_PURE_URL="https://github.com/${GH_USERNAME}/${GH_REPO_NAME}.git"
BRANCHES=(main docs/project-introduction refactor/zerotermux-adapter)

# ---------- 推送前检查 ----------
echo ""
echo "============================================================"
echo " 米游社工具箱 · 安全推送到 GitHub"
echo "============================================================"
info "仓库: $REPO_PURE_URL"
info "分支: ${BRANCHES[*]}"

git status --short | grep -q . && die "工作区有未提交改动。请先提交或 git stash。"
# 三个分支本地必须存在
for b in "${BRANCHES[@]}"; do
    git show-ref --verify --quiet "refs/heads/$b" || die "本地缺少分支 $b，先 git checkout -b 创建再运行"
done

# ---------- 鉴权配置 ----------
echo ""
info "[1/7] 临时安装 GitHub PAT（insteadOf 方式）：推送后立即清除"
install_insteadof "$GH_PAT"

echo ""
info "[2/7] 切换 origin（无 token 的纯 URL） -> $REPO_PURE_URL"
if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REPO_PURE_URL"
else
    git remote add origin "$REPO_PURE_URL"
fi
git remote -v | sed 's/^/  /'

echo ""
info "[3/7] 鉴权校验：对目标仓库执行 git ls-remote（只拉 refs，不写入）"
if ! git ls-remote --exit-code "$REPO_PURE_URL" HEAD >/dev/null 2>tmp_ls.err; then
    err "鉴权失败/仓库不存在："
    sed 's/^/    /' tmp_ls.err
    rm -f tmp_ls.err
    die "请检查：1) 仓库名是否拼写正确、大小写一致；2) 是否先在网页 Create repository 建好了空仓库（不勾选 README/ignore/license）；3) PAT 是否勾选了 repo 范围；4) PAT 是否过期/被撤销"
fi
rm -f tmp_ls.err
ok "鉴权通过：仓库存在 + PAT 对该仓库有读权限"

# ---------- Dry run ----------
echo ""
info "[4/7] 三分支 DRY-RUN（只检查，不真正推送数据对象）"
set -e
DRY_OK=1
for b in "${BRANCHES[@]}"; do
    echo -n "  $b  ->  "
    out=$(git push -u --dry-run origin "$b" 2>&1) || { echo "❌"; echo "$out" | sed 's/^/      /'; DRY_OK=0; continue; }
    lastline=$(tail -1 <<<"$out")
    echo "✅  $lastline"
done
[ "$DRY_OK" = "1" ] || die "--dry-run 存在失败项，已停止。请根据上面日志处理（常见是远端仓库被你初始化了 README，需要删除重建空仓库，或 git pull --allow-unrelated-histories）"

# ---------- 正式推送 ----------
echo ""
info "[5/7] 正式推送（逐个分支，-u 设置 upstream）"
for b in "${BRANCHES[@]}"; do
    echo "  $ git push -u origin $b"
    git push -u origin "$b"
    ok "分支 $b 推送完成"
done

# ---------- 远端回读校验 ----------
echo ""
info "[6/7] 远端回读：git ls-remote --heads origin"
REMOTE_HEADS=$(git ls-remote --heads origin)
echo "$REMOTE_HEADS" | sed 's/^/  /'
ALL_FOUND=1
for b in "${BRANCHES[@]}"; do
    if ! grep -q "refs/heads/${b}$" <<<"$REMOTE_HEADS"; then
        err "远端缺少分支: $b"
        ALL_FOUND=0
    fi
done
[ "$ALL_FOUND" = "1" ] || die "回读校验失败：不是三分支都在远端"
ok "三分支全部在远端存在"

# ---------- 收尾 ----------
echo ""
info "[7/7] 清除 token 残留 + 环境变量"
cleanup_token
ok "清理完成：insteadOf 已卸、origin URL 已保证无 token、GH_PAT 已 unset"

git remote -v | sed 's/^/  /'

echo ""
echo "============================================================"
ok "🎉 全部推送完成"
echo "   Web 查看仓库:  https://github.com/${GH_USERNAME}/${GH_REPO_NAME}"
echo "   查看分支列表:  https://github.com/${GH_USERNAME}/${GH_REPO_NAME}/branches"
echo "============================================================"
