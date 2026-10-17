# CLAUDE.md

Guidance for [Claude Code](https://claude.ai/code) in this repository.

Patterns follow [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) (Command → Agent → Skill, `.claude/rules/`, project settings). Optional full reference kit: `./scripts/install-claude-best-practice.sh`.

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

## Commands to run

```bash
# Transfer page / dev server (browser)
python3 site.py

# Self-check (site + helpers)
python3 site.py --self-test

# Build (after deps + icon.icns); see README
# pyinstaller SendToMac.spec  (arm + intel builds, then scripts/make-dmg.sh)
```

Do not commit secrets. Website download stats use GitHub Releases API (`web/lib/github-downloads.js`).

## Change discipline

- **Surgical diffs** — match existing style in `site.py`, `menu_app.py`, and `web/`.
- **Privacy** — no analytics, tracking cookies, or public upload paths unless explicitly requested.
- **macOS** — min OS 11.0 in bundle; Tahoe (26+) needs inside-out ad-hoc signing (see `scripts/codesign-macos-app.sh`, `make-dmg.sh`).
- **Tests** — prefer `python3 site.py --self-test` after server/protocol changes; load tests live under `loadtest/`.

## Claude Code layout

- `.claude/settings.json` — shared permissions and defaults
- `.claude/settings.local.json` — personal overrides (gitignored)
- `.claude/rules/` — always-on project rules
- `.claude/commands/` — slash commands for this repo

Use `/project-review` before large PRs and `/self-test` after server changes. For the upstream course demo (`/weather-orchestrator`, hooks, workflow agents), run `./scripts/install-claude-best-practice.sh`.
