#!/bin/zsh
# 每日拉取昨天的 flomo 笔记，保存为 Markdown
# 配置来源：~/.config/daily-notes/config.env（可用 DAILY_NOTES_CONFIG 环境变量覆盖路径）
# 由 LaunchAgent 定时调起；同名输出文件已存在时跳过，可随时手动补跑

set -u

CONFIG="${DAILY_NOTES_CONFIG:-$HOME/.config/daily-notes/config.env}"
[[ -f "$CONFIG" ]] || { echo "[flomo-daily] 缺少配置文件: $CONFIG" >&2; exit 1; }
source "$CONFIG"

: "${OUT_DIR:?config.env 中缺少 OUT_DIR}"
: "${FLOMO_AUTH:?config.env 中缺少 FLOMO_AUTH（token 过期请重新抓取并更新）}"
NODE_BIN="${NODE_BIN:-node}"
FLOMO_MCP_BIN="${FLOMO_MCP_BIN:-flomo-web-mcp}"
FLOMO_TIMEZONE="${FLOMO_TIMEZONE:-Asia/Shanghai}"

mkdir -p "$OUT_DIR"
LOG_FILE="$OUT_DIR/.flomo-daily.log"
YESTERDAY=$(date -v-1d +%Y-%m-%d)
OUT_FILE="$OUT_DIR/FLOMO-$YESTERDAY.md"

log() { print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

if [[ -f "$OUT_FILE" ]]; then
  log "SKIP: $OUT_FILE 已存在"
  exit 0
fi

export FLOMO_AUTHORIZATION="$FLOMO_AUTH" FLOMO_TIMEZONE="$FLOMO_TIMEZONE"

ITEMS=$("$NODE_BIN" --input-type=module -e '
import { spawn } from "node:child_process";
const [, yesterday, mcpBin] = process.argv;
const child = spawn(mcpBin, [], { env: { ...process.env }, stdio: ["pipe", "pipe", "pipe"] });
let buf = "";
const pending = new Map();
let id = 0;
child.stdout.on("data", (d) => {
  buf += d.toString();
  let i;
  while ((i = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, i);
    buf = buf.slice(i + 1);
    if (!line.trim()) continue;
    try {
      const msg = JSON.parse(line);
      if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    } catch {}
  }
});
child.stderr.on("data", () => {});
function send(method, params) {
  return new Promise((resolve) => {
    const mid = ++id;
    pending.set(mid, resolve);
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: mid, method, params }) + "\n");
  });
}
await new Promise((r) => setTimeout(r, 1000));
child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }) + "\n");
const res = await send("tools/call", { name: "list_notes", arguments: { limit: 100 } });
child.kill();
if (!res.result || res.result.isError) { console.error("FLOMO_FETCH_FAILED"); process.exit(1); }
const payload = JSON.parse(res.result.content[0].text);
if (!payload.ok) { console.error("FLOMO_NOT_OK"); process.exit(1); }
const items = (payload.items || []).filter((m) => m.createdAt && m.createdAt.startsWith(yesterday));
console.log(JSON.stringify(items));
' "$YESTERDAY" "$FLOMO_MCP_BIN" 2>/dev/null)

if [[ $? -ne 0 || -z "$ITEMS" ]]; then
  log "ERROR: 拉取失败（多为 token 过期或网络异常；请更新 $CONFIG 中的 FLOMO_AUTH 后重试）"
  exit 1
fi

COUNT=$(printf '%s' "$ITEMS" | "$NODE_BIN" -e '
const fs = require("fs");
let s = "";
process.stdin.on("data", (d) => (s += d));
process.stdin.on("end", () => {
  const items = JSON.parse(s);
  const lines = ["# flomo 日记 " + process.argv[1], ""];
  if (!items.length) {
    lines.push("> 昨天没有 flomo 记录。");
  } else {
    lines.push("> 共 " + items.length + " 条，由 flomo-daily 自动化于 " + new Date().toLocaleString("sv") + " 生成。", "");
    for (const m of items) {
      const tags = (m.tags || []).join(" ");
      lines.push("## " + m.createdAt.slice(11) + (tags ? " " + tags : ""), "", m.content || "", "");
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
