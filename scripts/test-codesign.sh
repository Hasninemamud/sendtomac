#!/bin/bash
# Tests for scripts/codesign-macos-app.sh and the launcher layout. Needs a built nested app
# (dist-intel/SendToMac.app or dist/SendToMac.app); synthetic cases run without one.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIGN="$ROOT/scripts/codesign-macos-app.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "ok   - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# --- synthetic bundle: launcher + nested app containing a dylib, with quarantine + junk ---
mk_app() { # dir name
  local app="$1/$2.app"; mkdir -p "$app/Contents/MacOS" "$app/Contents/Frameworks"
  printf 'int main(){return 0;}\n' > "$TMP/m.c"
  cc -o "$app/Contents/MacOS/SendToMac" "$TMP/m.c" || return 1
  cc -dynamiclib -o "$app/Contents/Frameworks/libx.dylib" "$TMP/m.c" 2>/dev/null || cc -dynamiclib -x c -o "$app/Contents/Frameworks/libx.dylib" - <<<'int f(){return 1;}'
  ln -s libx.dylib "$app/Contents/Frameworks/libx-link.dylib"
  cat > "$app/Contents/Info.plist" <<P
<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>SendToMac</string><key>CFBundleIdentifier</key><string>test.$2</string>
<key>CFBundlePackageType</key><string>APPL</string></dict></plist>
P
  mkdir -p "$app/Contents/Resources"; echo data > "$app/Contents/Resources/data.txt"; touch "$app/.DS_Store"
  xattr -w com.apple.quarantine "0081;00000000;Safari;" "$app" 2>/dev/null
}
mkdir -p "$TMP/with space"
mk_app "$TMP/with space" "Outer App" && ok "build synthetic app (space in path)" || bad "build synthetic app"
OUT="$TMP/with space/Outer App.app"
mkdir -p "$OUT/Contents/Resources/Intel"; mk_app "$OUT/Contents/Resources/Intel" "SendToMac"
NEST="$OUT/Contents/Resources/Intel/SendToMac.app"

check "usage error with no args (exit 2)" '"$SIGN" >/dev/null 2>&1; [ $? -eq 2 ]'
check "non-bundle: lenient exits 0" '"$SIGN" "$TMP" >/dev/null 2>&1'
check "non-bundle: --strict exits 1" '"$SIGN" --strict "$TMP" >/dev/null 2>&1; [ $? -eq 1 ]'
check "missing path: --strict exits 1" '"$SIGN" --strict "$TMP/nope.app" >/dev/null 2>&1; [ $? -eq 1 ]'

check "dual sign (nested then outer) succeeds" '"$SIGN" --strict "$NEST" "$OUT" >/dev/null 2>&1'
check "outer verifies --strict" 'codesign --verify --strict "$OUT" >/dev/null 2>&1'
check "outer verifies --deep --strict" 'codesign --verify --deep --strict "$OUT" >/dev/null 2>&1'
check "nested verifies --deep --strict" 'codesign --verify --deep --strict "$NEST" >/dev/null 2>&1'
check "quarantine xattr stripped" '! xattr -lr "$OUT" 2>/dev/null | grep -q quarantine'
check ".DS_Store removed" '[ ! -e "$OUT/.DS_Store" ]'
check "signature is ad-hoc" '[[ "$(codesign -dv "$OUT" 2>&1)" == *Signature=adhoc* ]]'
check "no hardened runtime flag" '[[ "$(codesign -dv "$OUT" 2>&1)" != *runtime* ]]'
check "symlink not signed as separate file (dylib still intact)" '[ -L "$NEST/Contents/Frameworks/libx-link.dylib" ]'
check "idempotent re-run" '"$SIGN" --strict "$NEST" "$OUT" >/dev/null 2>&1 && codesign --verify --strict "$OUT" >/dev/null 2>&1'

# Corner: re-copy of signed nested app (what make-dmg does) then tamper => verify must fail, resign must heal
echo tamper >> "$NEST/Contents/Resources/data.txt"
check "tamper breaks outer seal" '! codesign --verify --strict "$OUT" >/dev/null 2>&1'
"$SIGN" --strict "$NEST" "$OUT" >/dev/null 2>&1
check "resign heals tampered bundle" 'codesign --verify --strict "$OUT" >/dev/null 2>&1'

# Corner: quarantine re-added after signing (download) is cleared by installer-style pass
xattr -w com.apple.quarantine "0081;00000000;Safari;" "$OUT" 2>/dev/null
"$SIGN" --strict "$NEST" "$OUT" >/dev/null 2>&1
check "re-quarantined bundle cleaned and valid" '! xattr -l "$OUT" | grep -q quarantine && codesign --verify --strict "$OUT" >/dev/null 2>&1'

# Corner: Mach-O with wrong extension is still signed (found via file(1), not name)
cp "$NEST/Contents/Frameworks/libx.dylib" "$NEST/Contents/Frameworks/blob.bin"
"$SIGN" --strict "$NEST" "$OUT" >/dev/null 2>&1
check "Mach-O without .dylib/.so extension signed" '[[ "$(codesign -dv "$NEST/Contents/Frameworks/blob.bin" 2>&1)" == *adhoc* ]]'

# --- launcher: compiles for both arches; resolves sibling path layout ---
check "launcher.c compiles (arm64)" 'cc -arch arm64 -o "$TMP/l-arm" "$ROOT/launcher.c" 2>/dev/null'
check "launcher.c compiles (x86_64)" 'cc -arch x86_64 -o "$TMP/l-x86" "$ROOT/launcher.c" 2>/dev/null'
if [ -x "$TMP/l-arm" ]; then
  mkdir -p "$TMP/pkg/Contents/MacOS" "$TMP/pkg/Contents/Resources/AppleSilicon/SendToMac.app/Contents/MacOS"
  cp "$TMP/l-arm" "$TMP/pkg/Contents/MacOS/SendToMac"
  printf '#!/bin/sh\necho launched-nested\n' > "$TMP/pkg/Contents/Resources/AppleSilicon/SendToMac.app/Contents/MacOS/SendToMac"
  chmod +x "$TMP/pkg/Contents/Resources/AppleSilicon/SendToMac.app/Contents/MacOS/SendToMac"
  if [ "$(uname -m)" = arm64 ]; then
    check "launcher execs nested AppleSilicon binary" '[ "$("$TMP/pkg/Contents/MacOS/SendToMac")" = launched-nested ]'
  fi
  rm "$TMP/pkg/Contents/Resources/AppleSilicon/SendToMac.app/Contents/MacOS/SendToMac"
  check "launcher fails cleanly when nested app missing" '"$TMP/pkg/Contents/MacOS/SendToMac" >/dev/null 2>&1; [ $? -eq 1 ]'
fi

# --- real build, if present ---
for REAL in "$ROOT/dist/SendToMac.app" "$ROOT/dist-intel/SendToMac.app"; do
  [ -d "$REAL" ] || continue
  cp -R "$REAL" "$TMP/real.app"
  "$SIGN" --strict "$TMP/real.app" >/dev/null 2>&1
  check "real build signs + verifies: ${REAL#$ROOT/}" 'codesign --verify --deep --strict "$TMP/real.app" >/dev/null 2>&1'
  rm -rf "$TMP/real.app"
done

# --- installer script and make-dmg parse ---
check "make-dmg.sh syntax" 'bash -n "$ROOT/scripts/make-dmg.sh"'
check "installer syntax" 'bash -n "$ROOT/Install SendToMac.command"'
check "make-dmg.sh no longer uses --deep to sign" '! grep -E "codesign .*--force --deep" "$ROOT/scripts/make-dmg.sh"'
check "installer no longer uses --deep to sign" '! grep -E "codesign .*--force --deep" "$ROOT/Install SendToMac.command"'

echo "---- $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
