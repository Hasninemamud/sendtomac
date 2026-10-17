#!/bin/bash
# Ad-hoc sign a .app inside-out (macOS 26 Tahoe safe): every nested Mach-O first,
# then nested bundles deepest-first, then the outer app. No --deep, no hardened runtime.
# Usage: codesign-macos-app.sh [--strict] APP [APP...]   (list nested apps before outer apps)
#   --strict  exit non-zero on any signing failure (default: warn and continue)
# Also sourced by Install SendToMac.command logic — keep behaviour in sync.
set -uo pipefail

STRICT=0
if [ "${1:-}" = "--strict" ]; then STRICT=1; shift; fi
[ $# -ge 1 ] || { echo "usage: $0 [--strict] App.app [...]" >&2; exit 2; }

FAILED=0
sign_one() {
  if ! codesign --force --sign - --timestamp=none "$1" >/dev/null 2>&1; then
    echo "codesign failed: $1" >&2
    FAILED=1
  fi
}

sign_app() {
  local app="${1%/}"
  [ -d "$app/Contents" ] || { echo "not an app bundle: $app" >&2; FAILED=1; return; }
  # Quarantine / resource forks / Finder junk invalidate seals on Tahoe.
  xattr -cr "$app" 2>/dev/null || true
  find "$app" -name .DS_Store -delete 2>/dev/null || true
  local main
  main="$app/Contents/MacOS/$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist" 2>/dev/null || echo SendToMac)"

  # 1) Loose Mach-O files (dylib/.so/helpers), deepest first; skip symlinks and the main exe.
  while IFS= read -r f; do
    [ "$f" = "$main" ] && continue
    file -b "$f" 2>/dev/null | grep -q 'Mach-O' && sign_one "$f"
  done < <(find "$app" -type f ! -type l -print | awk -F/ '{print NF "\t" $0}' | sort -rn | cut -f2-)

  # 2) Nested bundles (frameworks, helper apps, plug-ins), deepest first.
  while IFS= read -r b; do
    [ "$b" = "$app" ] && continue
    sign_one "$b"
  done < <(find "$app" -type d \( -name '*.framework' -o -name '*.app' -o -name '*.appex' -o -name '*.xpc' \) \
             | awk -F/ '{print NF "\t" $0}' | sort -rn | cut -f2-)

  # 3) Main executable, then the bundle itself.
  [ -f "$main" ] && sign_one "$main"
  sign_one "$app"
  codesign --verify --strict "$app" >/dev/null 2>&1 || { echo "verify failed: $app" >&2; FAILED=1; }
}

for a in "$@"; do sign_app "$a"; done

if [ "$FAILED" -ne 0 ]; then
  [ "$STRICT" -eq 1 ] && exit 1
  echo "warning: some signing steps failed" >&2
fi
exit 0
