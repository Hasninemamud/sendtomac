# CLAUDE.md

Guidance for working on **SendToMac** in this repository.

## Product

SendToMac moves files between a phone (browser) and a Mac on the same Wi‑Fi. No account, no public file host.

| Area | Path | Notes |
|------|------|--------|
| Local server + landing | `site.py` | Port `8790`, WebSocket relay, `/api/*` for app |
| Legacy / alternate server | `sendtomac.py` | Older entry; prefer `site.py` for web + app |
| Menu-bar UI | `menu_app.py` | PyObjC, WKWebView popover, drag-drop |
| Staging uploads | `staging.py` | Used by menu web view |
| Marketing site | `web/` | Static + Vercel serverless `web/api/` |
| macOS bundle | `SendToMac.spec`, `launcher.c`, `scripts/make-dmg.sh` | Universal outer app → nested arch PyInstaller apps |

Received files: `~/Downloads/SendToMac`. Max file **500 MB**, note **20,000** chars.

## Commands

```bash
python3 site.py
python3 site.py --self-test
# Build: pyinstaller SendToMac.spec (arm + intel), then ./scripts/make-dmg.sh
```

Do not commit secrets. Download stats use GitHub Releases API (`web/lib/github-downloads.js`).

## Change discipline

- Surgical diffs — match style in `site.py`, `menu_app.py`, `web/`.
- Privacy — no analytics or tracking cookies unless explicitly requested.
- macOS min 11.0; Tahoe signing via `scripts/codesign-macos-app.sh` and `make-dmg.sh`.
- After server/protocol changes: `python3 site.py --self-test`.
