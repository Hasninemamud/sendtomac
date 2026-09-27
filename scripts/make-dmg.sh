#!/bin/bash
# Assemble dual-arch SendToMac.app, ad-hoc sign (fixes Gatekeeper "damaged"), build styled DMG.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${SENDTOMAC_VERSION:-2.4.2}"
PKG="$ROOT/dist/package/SendToMac.app"
STAGE="$ROOT/dist/dmg-source"
OUT="$ROOT/dist/SendToMac.dmg"
BG="$ROOT/assets/dmg-background.png"

need() { test -d "$1" || { echo "missing: $1 — build apps first"; exit 1; }; }
need "$ROOT/dist/SendToMac.app"
need "$ROOT/dist-intel/SendToMac.app"
test -f "$BG" || { echo "missing: $BG"; exit 1; }
command -v create-dmg >/dev/null || { echo "install create-dmg (brew install create-dmg)"; exit 1; }

echo "==> Assemble dual-arch package ($VERSION)"
mkdir -p "$PKG/Contents/MacOS" "$PKG/Contents/Resources/AppleSilicon" "$PKG/Contents/Resources/Intel"
# Keep existing universal launcher if present; otherwise require it.
test -x "$PKG/Contents/MacOS/SendToMac" || {
  echo "missing launcher binary at $PKG/Contents/MacOS/SendToMac"
  exit 1
}
rm -rf "$PKG/Contents/Resources/AppleSilicon/SendToMac.app" "$PKG/Contents/Resources/Intel/SendToMac.app"
cp -R "$ROOT/dist/SendToMac.app" "$PKG/Contents/Resources/AppleSilicon/SendToMac.app"
cp -R "$ROOT/dist-intel/SendToMac.app" "$PKG/Contents/Resources/Intel/SendToMac.app"
cp -f "$ROOT/icon.icns" "$PKG/Contents/Resources/icon.icns"

# Outer Info.plist
cat > "$PKG/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDisplayName</key><string>SendToMac</string>
	<key>CFBundleExecutable</key><string>SendToMac</string>
	<key>CFBundleIconFile</key><string>icon.icns</string>
	<key>CFBundleIdentifier</key><string>app.sendtomac</string>
	<key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
	<key>CFBundleName</key><string>SendToMac</string>
	<key>CFBundlePackageType</key><string>APPL</string>
	<key>CFBundleShortVersionString</key><string>${VERSION}</string>
	<key>CFBundleVersion</key><string>${VERSION}</string>
	<key>LSMinimumSystemVersion</key><string>11.0</string>
	<key>LSUIElement</key><true/>
	<key>NSHighResolutionCapable</key><true/>
	<key>NSLocalNetworkUsageDescription</key>
	<string>SendToMac uses your Wi-Fi so the phone can scan the code and send a file.</string>
</dict>
</plist>
EOF

echo "==> Ad-hoc sign (nested → outer)"
# Copying nested apps breaks any previous seal; resign in order.
codesign --force --deep --sign - "$PKG/Contents/Resources/AppleSilicon/SendToMac.app"
codesign --force --deep --sign - "$PKG/Contents/Resources/Intel/SendToMac.app"
codesign --force --deep --sign - "$PKG"
codesign --verify --deep --strict "$PKG"
echo "signature ok"

echo "==> Stage DMG contents"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$PKG" "$STAGE/SendToMac.app"
# Classic drag-to-Applications layout (no shell installer in the window).
xattr -cr "$STAGE" 2>/dev/null || true

echo "==> Build styled DMG"
rm -f "$OUT"
# Window 660×420; app left, Applications right.
create-dmg \
  --volname "SendToMac" \
  --volicon "$ROOT/icon.icns" \
  --background "$BG" \
  --window-pos 200 120 \
  --window-size 660 420 \
  --icon-size 112 \
  --icon "SendToMac.app" 150 170 \
  --hide-extension "SendToMac.app" \
  --app-drop-link 510 170 \
  --no-internet-enable \
  "$OUT" \
  "$STAGE"

# create-dmg leaves the source folder as the app root; ensure Install is only once
xattr -cr "$OUT" 2>/dev/null || true
ls -lh "$OUT"
echo "==> Done: $OUT"
