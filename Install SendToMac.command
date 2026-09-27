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
xattr -cr "$DEST" 2>/dev/null || true
if [ -d "$DEST/Contents/Resources/AppleSilicon/SendToMac.app" ]; then
  codesign --force --deep --sign - "$DEST/Contents/Resources/AppleSilicon/SendToMac.app" 2>/dev/null || true
fi
if [ -d "$DEST/Contents/Resources/Intel/SendToMac.app" ]; then
  codesign --force --deep --sign - "$DEST/Contents/Resources/Intel/SendToMac.app" 2>/dev/null || true
fi
codesign --force --deep --sign - "$DEST" 2>/dev/null || true

open "$DEST"

osascript -e 'display dialog "SendToMac is in Applications and should appear in the menu bar.\n\nClick the icon to open it. If macOS ever says the app is damaged, run this installer again (or right-click the app → Open)." buttons {"OK"} default button 1 with title "SendToMac installed"' >/dev/null 2>&1 || true
echo "Installed to $DEST"
