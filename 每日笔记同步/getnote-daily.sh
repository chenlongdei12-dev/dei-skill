#!/bin/zsh
# 每日拉取昨天的得到大脑（GetNote）笔记，保存为 Markdown
# 配置来源：~/.config/daily-notes/config.env
# 依赖：getnote CLI 已安装并完成 `getnote auth login` 授权

set -u

CONFIG="${DAILY_NOTES_CONFIG:-$HOME/.config/daily-notes/config.env}"
[[ -f "$CONFIG" ]] || { echo "[getnote-daily] 缺少配置文件: $CONFIG" >&2; exit 1; }
source "$CONFIG"

: "${OUT_DIR:?config.env 中缺少 OUT_DIR}"
GETNOTE_BIN="${GETNOTE_BIN:-getnote}"
NODE_BIN="${NODE_BIN:-node}"

mkdir -p "$OUT_DIR"
LOG_FILE="$OUT_DIR/.getnote-daily.log"
YESTERDAY=$(date -v-1d +%Y-%m-%d)
OUT_FILE="$OUT_DIR/GETNOTE-$YESTERDAY.md"

log() { print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

if [[ -f "$OUT_FILE" ]]; then
  log "SKIP: $OUT_FILE 已存在"
  exit 0
fi

RAW=$("$GETNOTE_BIN" notes --limit 50 -o json 2>/dev/null)
if [[ $? -ne 0 || -z "$RAW" ]]; then
  log "ERROR: getnote notes 拉取失败（未授权或网络异常；可用 $GETNOTE_BIN doctor 诊断）"
  exit 1
fi

COUNT=$(printf '%s' "$RAW" | "$NODE_BIN" -e '
const fs = require("fs");
let s = "";
process.stdin.on("data", (d) => (s += d));
process.stdin.on("end", () => {
  let notes = [];
  try { notes = (JSON.parse(s).data || {}).notes || []; }
  catch (e) { console.error("PARSE_FAILED"); process.exit(1); }
  const items = notes.filter((n) => (n.created_at || "").startsWith(process.argv[1]));
  const lines = ["# 得到大脑日记 " + process.argv[1], ""];
  if (!items.length) {
    lines.push("> 昨天没有得到大脑记录。");
  } else {
    lines.push("> 共 " + items.length + " 条，由 getnote-daily 自动化于 " + new Date().toLocaleString("sv") + " 生成。", "");
    for (const n of items) {
      const time = (n.created_at || "").slice(11, 19);
      const tags = (n.tags || []).map((t) => "#" + t.name).join(" ");
      lines.push("## " + time + " " + (n.title || "无标题") + (tags ? " " + tags : ""), "");
      if (n.note_url) lines.push("[原始笔记](" + n.note_url + ")", "");
      const content = n.content || "";
      if (content.length > 3000) {
        lines.push(content.slice(0, 3000), "", "...（内容过长已截断，查看原文）");
      } else {
        lines.push(content);
      }
      lines.push("");
    }
  }
  fs.writeFileSync(process.argv[2], lines.join("\n"));
  console.log(items.length);
});' "$YESTERDAY" "$OUT_FILE")

if [[ -z "$COUNT" ]]; then
  log "ERROR: 解析/写入失败: $OUT_FILE"
  exit 1
fi

log "OK: $OUT_FILE ($COUNT 条)"
