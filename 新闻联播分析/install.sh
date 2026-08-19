#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${OPENCODE_SKILLS_DIR:-$HOME/.config/opencode/skills}"
TARGET="$SKILLS_DIR/news-broadcast-analysis"

mkdir -p "$TARGET"
cp -R "$SCRIPT_DIR/." "$TARGET/"

printf 'Installed news-broadcast-analysis to %s\n' "$TARGET"
