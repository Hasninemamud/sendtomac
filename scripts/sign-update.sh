#!/bin/bash
# Sign a release DMG so installed apps accept it as an update: writes <dmg>.sig next to it.
# Upload BOTH files to the GitHub release. The private key stays outside the repo (back it up:
# without it, installed apps can never accept another update). Public half lives in site.py.
set -euo pipefail
DMG="${1:?usage: sign-update.sh path/to/SendToMac.dmg}"
KEY="${SENDTOMAC_UPDATE_KEY:-$HOME/.sendtomac/update-signing-key.pem}"
[ -f "$KEY" ] || { echo "missing signing key: $KEY" >&2; exit 1; }
/usr/bin/openssl dgst -sha256 -sign "$KEY" -out "$DMG.sig" "$DMG"
echo "signed: $DMG.sig"
