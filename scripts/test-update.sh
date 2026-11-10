#!/bin/bash
# Sandbox test of the in-app updater (site.install_update): builds a real fake DMG, signs it with a
# throwaway key, installs into a temp folder, and stubs killall/open so the running app is never touched.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/src" "$T/Apps" "$T/tmp"
for n in killall open; do printf '#!/bin/sh\necho "%s $@" >> "%s/calls.log"\n' "$n" "$T" > "$T/bin/$n"; chmod +x "$T/bin/$n"; done

mk_app() { # dir marker  -> dir/SendToMac.app (outer) wrapping Resources/AppleSilicon/SendToMac.app, like the real bundle
  local c="$1/SendToMac.app/Contents"; mkdir -p "$c/MacOS" "$c/Resources/AppleSilicon/SendToMac.app/Contents/MacOS"
  printf '#!/bin/sh\necho %s\n' "$2" > "$c/MacOS/SendToMac"; chmod +x "$c/MacOS/SendToMac"
  : > "$c/Resources/AppleSilicon/SendToMac.app/Contents/MacOS/SendToMac"
  printf '<?xml version="1.0"?><plist version="1.0"><dict><key>CFBundleExecutable</key><string>SendToMac</string><key>CFBundleIdentifier</key><string>app.sendtomac.test</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>' > "$c/Info.plist"
  codesign --force --sign - "$1/SendToMac.app" >/dev/null 2>&1
}
mk_app "$T/src" NEW; mk_app "$T/Apps" OLD
hdiutil create -quiet -srcfolder "$T/src" -volname SendToMac -fs HFS+ "$T/good.dmg"
cp "$T/good.dmg" "$T/tampered.dmg"; cp "$T/good.dmg" "$T/wrongkey.dmg"; cp "$T/good.dmg" "$T/unsigned.dmg"

/usr/bin/openssl ecparam -name prime256v1 -genkey -noout -out "$T/key.pem"
/usr/bin/openssl ecparam -name prime256v1 -genkey -noout -out "$T/other.pem"
/usr/bin/openssl ec -in "$T/key.pem" -pubout -out "$T/pub.pem" 2>/dev/null
SENDTOMAC_UPDATE_KEY="$T/key.pem" "$ROOT/scripts/sign-update.sh" "$T/good.dmg" >/dev/null
SENDTOMAC_UPDATE_KEY="$T/key.pem" "$ROOT/scripts/sign-update.sh" "$T/tampered.dmg" >/dev/null
SENDTOMAC_UPDATE_KEY="$T/other.pem" "$ROOT/scripts/sign-update.sh" "$T/wrongkey.dmg" >/dev/null
echo "extra bytes after signing" >> "$T/tampered.dmg"

TMPDIR="$T/tmp" PATH="$T/bin:$PATH" python3 -I - "$ROOT" "$T" <<'EOF'
import importlib.util, os, pathlib, sys, time
root, t = sys.argv[1], pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("sendsite", f"{root}/site.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.UPDATE_PUBKEY = (t / "pub.pem").read_text()
app = (t / "Apps" / "SendToMac.app").resolve()  # /var -> /private/var: installed_app() returns the real path
nested_exe = app / "Contents/Resources/AppleSilicon/SendToMac.app/Contents/MacOS/SendToMac"
version = lambda: os.popen(str(app / "Contents/MacOS/SendToMac")).read().strip()
def fails(label, expect=""):
    try: m.install_update()
    except RuntimeError as e:
        assert expect in str(e), f"{label}: unexpected error {e}"; return print("ok   -", label)
    raise SystemExit("FAIL - " + label)
def untouched():
    assert version() == "OLD" and [p.name for p in (t / "Apps").iterdir()] == ["SendToMac.app"], "old app disturbed"
    assert not list((t / "tmp").glob("sendtomac-update-*")), "temp dir leaked"

fails("refuses when not running as the app", "only from the SendToMac app")
sys.frozen = True
sys.executable = "/Volumes/SendToMac/SendToMac.app/Contents/MacOS/SendToMac"
fails("refuses to update from a mounted disk image", "Move SendToMac to Applications")
sys.executable = str(nested_exe)
assert m.installed_app() == app; print("ok   - finds the outer app from the nested binary")

for name, expect in (("tampered", "signature is not valid"), ("wrongkey", "signature is not valid"), ("unsigned", "")):
    m.DMG_DOWNLOAD_URL = (t / f"{name}.dmg").as_uri()
    fails(f"{name} DMG rejected", expect); untouched()
print("ok   - old app untouched after every rejection")

m.DMG_DOWNLOAD_URL = (t / "good.dmg").as_uri(); m.install_update()
for _ in range(60):
    if version() == "NEW" and (t / "calls.log").exists() and "open" in (t / "calls.log").read_text(): break
    time.sleep(0.2)
assert version() == "NEW"; print("ok   - signed update swapped in")
assert [p.name for p in (t / "Apps").iterdir()] == ["SendToMac.app"]; print("ok   - no staged/.old leftovers")
calls = (t / "calls.log").read_text(); assert "killall SendToMac" in calls and f"open {app}" in calls; print("ok   - quit old app, relaunched new")
assert not list((t / "tmp").glob("sendtomac-update-*")); print("ok   - temp download removed")
EOF
