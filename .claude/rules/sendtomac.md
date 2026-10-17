# SendToMac project rules

## Scope

- Menu-bar Mac app + local HTTP/WebSocket server + static marketing site (`web/`).
- Files stay on the LAN; do not add cloud upload, accounts, or analytics without an explicit product request.

## Code

- Python 3, PyObjC (`menu_app.py`), PyInstaller (`SendToMac.spec`). Web: static HTML/CSS/JS; Vercel functions in `web/api/`.
- One pairing session at a time; respect `MAX_FILE`, `MAX_TEXT`, and safe filename rules in `site.py`.
- When editing signing/DMG flow, use inside-out ad-hoc `codesign` (no hardened runtime with ad-hoc). Nested bundle: outer launcher → `Resources/{AppleSilicon,Intel}/SendToMac.app`.

## Verification

- After protocol or handler changes: `python3 site.py --self-test`.
- After `web/` API or landing changes: confirm `/api/downloads` and `/api/download` behavior.

## Docs

- User-facing copy: plain language, no tracking. Privacy claims must match `web/privacy/index.html`.
