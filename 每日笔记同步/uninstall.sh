#!/bin/zsh
# 卸载 daily-notes-sync：移除 LaunchAgent、脚本、配置（已生成的笔记文件保留）
set -u

for name in flomo getnote; do
  launchctl bootout "gui/$(id -u)/com.dailynotes.$name" 2>/dev/null
  rm -f "$HOME/Library/LaunchAgents/com.dailynotes.$name.plist"
done
rm -f "$HOME/.local/bin/flomo-daily.sh" "$HOME/.local/bin/getnote-daily.sh"

CONFIG="$HOME/.config/daily-notes/config.env"
[[ -f "$CONFIG" ]] && rm -f "$CONFIG" && echo "已删除配置 $CONFIG"

echo "卸载完成（已生成的笔记文件保留在原目录）"
