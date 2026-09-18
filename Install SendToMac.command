#!/bin/bash
# Install SendToMac into Applications and clear the download quarantine flag.
set -e
cd "$(dirname "$0")"

APP="SendToMac.app"
if [ ! -d "$APP" ]; then
  osascript -e 'display dialog "Put Install SendToMac.command next to SendToMac.app inside the disk image, then try again." buttons {"OK"} default button 1 with title "SendToMac"' >/dev/null 2>&1 || true
  echo "SendToMac.app not found next to this installer."
  exit 1
fi

DEST="/Applications/SendToMac.app"
rm -rf "$DEST"
cp -R "$APP" "$DEST"
xattr -cr "$DEST" 2>/dev/null || true
open "$DEST"

osascript -e 'display dialog "SendToMac is in Applications and should appear in the menu bar.\n\nClick the icon to open it. On first launch, use the menu-bar icon — Option⌘ is optional (enable from the right-click menu)." buttons {"OK"} default button 1 with title "SendToMac installed"' >/dev/null 2>&1 || true
echo "Installed to $DEST"
