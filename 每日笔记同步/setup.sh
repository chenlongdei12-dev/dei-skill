#!/bin/zsh
# daily-notes-sync 安装器：写配置 → 装脚本 → 注册 LaunchAgent
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

OUT_DIR=""
FLOMO_AUTH=""
FLOMO_TIME="09:00"
GETNOTE_TIME="09:05"
TIMEZONE="Asia/Shanghai"
SKIP_FLOMO=0
SKIP_GETNOTE=0

usage() {
  cat <<'EOF'
用法: setup.sh --out-dir <目录> [选项]

必选:
  --out-dir DIR         笔记保存目录（支持 ~ 开头）

可选:
  --flomo-auth STR      flomo Authorization 头（如 "Bearer xxx"；安装 flomo 部分时必填）
  --flomo-time HH:MM    flomo 拉取时间，默认 09:00
  --getnote-time HH:MM  得到大脑拉取时间，默认 09:05
  --tz ZONE             时区，默认 Asia/Shanghai
  --skip-flomo          不安装 flomo 部分
  --skip-getnote        不安装得到大脑部分
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir) OUT_DIR="${2:?缺少值}"; shift 2 ;;
    --flomo-auth) FLOMO_AUTH="${2:?缺少值}"; shift 2 ;;
    --flomo-time) FLOMO_TIME="${2:?缺少值}"; shift 2 ;;
    --getnote-time) GETNOTE_TIME="${2:?缺少值}"; shift 2 ;;
    --tz) TIMEZONE="${2:?缺少值}"; shift 2 ;;
    --skip-flomo) SKIP_FLOMO=1; shift ;;
    --skip-getnote) SKIP_GETNOTE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage; exit 1 ;;
  esac
done

[[ -n "$OUT_DIR" ]] || { usage; exit 1; }
OUT_DIR="${OUT_DIR/#\~/$HOME}"
mkdir -p "$OUT_DIR"

NODE_BIN="$(command -v node || true)"
[[ -n "$NODE_BIN" ]] || { echo "ERROR: 未找到 node（需要 Node.js >= 20）" >&2; exit 1; }

FLOMO_MCP_BIN=""
if [[ $SKIP_FLOMO -eq 0 ]]; then
  [[ -n "$FLOMO_AUTH" ]] || { echo "ERROR: 安装 flomo 部分需要 --flomo-auth（或用 --skip-flomo 跳过）" >&2; exit 1; }
  FLOMO_MCP_BIN="$(command -v flomo-web-mcp || true)"
  [[ -n "$FLOMO_MCP_BIN" ]] || { echo "ERROR: 未找到 flomo-web-mcp，请先: npm install -g flomo-web-mcp" >&2; exit 1; }
fi

GETNOTE_BIN=""
if [[ $SKIP_GETNOTE -eq 0 ]]; then
  GETNOTE_BIN="$(command -v getnote || true)"
  [[ -n "$GETNOTE_BIN" ]] || { echo "ERROR: 未找到 getnote，请先: npm install -g @getnote/cli@latest && getnote auth login" >&2; exit 1; }
fi

CONFIG_DIR="$HOME/.config/daily-notes"
CONFIG="$CONFIG_DIR/config.env"
BIN_DIR="$HOME/.local/bin"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$CONFIG_DIR" "$BIN_DIR" "$LAUNCH_DIR"

{
  printf '# daily-notes-sync 本机配置（自动生成，含敏感 token，勿提交/勿外传）\n'
  printf 'OUT_DIR=%q\n' "$OUT_DIR"
  if [[ $SKIP_FLOMO -eq 0 ]]; then
    printf 'FLOMO_AUTH=%q\n' "$FLOMO_AUTH"
    printf 'FLOMO_MCP_BIN=%q\n' "$FLOMO_MCP_BIN"
  fi
  if [[ $SKIP_GETNOTE -eq 0 ]]; then
    printf 'GETNOTE_BIN=%q\n' "$GETNOTE_BIN"
  fi
  printf 'FLOMO_TIMEZONE=%q\n' "$TIMEZONE"
  printf 'NODE_BIN=%q\n' "$NODE_BIN"
} > "$CONFIG"
chmod 600 "$CONFIG"

install_agent() {
  local name="$1" script="$2" hhmm="$3"
  local hh=$((10#${hhmm%%:*})) mm=$((10#${hhmm##*:}))
  local plist="$LAUNCH_DIR/com.dailynotes.$name.plist"
  sed -e "s|__SCRIPT__|$script|g" \
      -e "s|__HOUR__|$hh|g" -e "s|__MINUTE__|$mm|g" \
      "$SKILL_DIR/templates/com.dailynotes.$name.plist" > "$plist"
  launchctl bootout "gui/$(id -u)/com.dailynotes.$name" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  echo "✓ LaunchAgent com.dailynotes.$name → 每天 $hhmm 运行"
}

if [[ $SKIP_FLOMO -eq 0 ]]; then
  cp "$SKILL_DIR/flomo-daily.sh" "$BIN_DIR/flomo-daily.sh"
  chmod +x "$BIN_DIR/flomo-daily.sh"
  install_agent flomo "$BIN_DIR/flomo-daily.sh" "$FLOMO_TIME"
fi

if [[ $SKIP_GETNOTE -eq 0 ]]; then
  cp "$SKILL_DIR/getnote-daily.sh" "$BIN_DIR/getnote-daily.sh"
  chmod +x "$BIN_DIR/getnote-daily.sh"
  install_agent getnote "$BIN_DIR/getnote-daily.sh" "$GETNOTE_TIME"
fi

echo ""
echo "安装完成。"
echo "  配置:   $CONFIG"
echo "  输出:   $OUT_DIR/FLOMO-YYYY-MM-DD.md / GETNOTE-YYYY-MM-DD.md"
echo "  手动测试: $BIN_DIR/flomo-daily.sh && $BIN_DIR/getnote-daily.sh"
echo "  日志:   $OUT_DIR/.flomo-daily.log / .getnote-daily.log"
