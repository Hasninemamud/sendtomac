#!/bin/bash
# Install SendToMac into Applications, clear quarantine, and refresh ad-hoc signature.
# Double-click this from the DMG — do not only drag the app if macOS says it is "damaged".
set -e
cd "$(dirname "$0")"

APP="SendToMac.app"
if [ ! -d "$APP" ]; then
  osascript -e 'display dialog "Put Install SendToMac.command next to SendToMac.app inside the disk image, then try again." buttons {"OK"} default button 1 with title "SendToMac"' >/dev/null 2>&1 || true
  echo "SendToMac.app not found next to this installer."
  exit 1
fi

DEST="/Applications/SendToMac.app"
# Quit a running copy so replace succeeds.
killall SendToMac 2>/dev/null || true
sleep 0.3
rm -rf "$DEST"
cp -R "$APP" "$DEST"

# Gatekeeper "damaged" = quarantine and/or broken seal after download. Fix both.
# Sign inside-out (Tahoe/macOS 26): nested Mach-O -> nested apps -> outer app. No --deep.
# Keep in sync with scripts/codesign-macos-app.sh.
sign_one() { codesign --force --sign - --timestamp=none "$1" >/dev/null 2>&1 || echo "codesign failed: $1" >&2; }
sign_app() {
  local app="${1%/}" main="${1%/}/Contents/MacOS/SendToMac"
  [ -d "$app/Contents" ] || return 0
  xattr -cr "$app" 2>/dev/null || true
  while IFS= read -r f; do
    [ "$f" = "$main" ] && continue
    file -b "$f" 2>/dev/null | grep -q 'Mach-O' && sign_one "$f"
  done < <(find "$app" -type f ! -type l | awk -F/ '{print NF "\t" $0}' | sort -rn | cut -f2-)
  while IFS= read -r b; do
    [ "$b" = "$app" ] || sign_one "$b"
  done < <(find "$app" -type d \( -name '*.framework' -o -name '*.app' -o -name '*.appex' -o -name '*.xpc' \) | awk -F/ '{print NF "\t" $0}' | sort -rn | cut -f2-)
  [ -f "$main" ] && sign_one "$main"
  sign_one "$app"
}
sign_app "$DEST/Contents/Resources/AppleSilicon/SendToMac.app"
sign_app "$DEST/Contents/Resources/Intel/SendToMac.app"
sign_app "$DEST"
if ! codesign --verify --strict "$DEST" 2>/dev/null; then
  echo "warning: signature verification failed for $DEST" >&2
fi

open "$DEST"

osascript -e 'display dialog "SendToMac is in Applications and should appear in the menu bar.\n\nClick the icon to open it. If macOS ever says the app is damaged, run this installer again (or right-click the app → Open)." buttons {"OK"} default button 1 with title "SendToMac installed"' >/dev/null 2>&1 || true
echo "Installed to $DEST"
