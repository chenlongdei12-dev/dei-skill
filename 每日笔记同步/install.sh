#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${OPENCODE_SKILLS_DIR:-$HOME/.config/opencode/skills}"
TARGET="$SKILLS_DIR/daily-notes-sync"

mkdir -p "$TARGET"
cp -R "$SCRIPT_DIR/." "$TARGET/"
chmod +x "$TARGET"/*.sh 2>/dev/null || true

printf 'Installed daily-notes-sync to %s\n' "$TARGET"
