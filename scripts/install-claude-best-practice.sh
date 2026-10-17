#!/bin/bash
# Merge upstream claude-code-best-practice .claude/ into this repo (optional demo kit).
# https://github.com/shanraisshan/claude-code-best-practice
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="${TMPDIR:-/tmp}/claude-code-best-practice-$$"
REF="${1:-main}"

cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "==> Clone shanraisshan/claude-code-best-practice ($REF)"
git clone --depth 1 --branch "$REF" \
  https://github.com/shanraisshan/claude-code-best-practice.git "$TMP"

echo "==> Merge .claude/ (keep local settings.json and rules/sendtomac.md)"
mkdir -p "$ROOT/.claude"
rsync -a \
  --exclude='settings.json' \
  --exclude='rules/sendtomac.md' \
  --exclude='rules/claude-code-best-practice.md' \
  "$TMP/.claude/" "$ROOT/.claude/"

echo "==> Done. Upstream demo commands (e.g. /weather-orchestrator) are available."
echo "    SendToMac-specific: CLAUDE.md, .claude/settings.json, .claude/rules/sendtomac.md"
echo "    Re-run anytime to refresh upstream agents/skills/hooks."
