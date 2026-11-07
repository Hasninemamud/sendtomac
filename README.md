<p align="center">
  <img src="assets/logo-source.png" alt="SendToMac logo" width="128">
</p>

<h1 align="center">SendToMac</h1>

<p align="center">
  <b>Scan a code, send a file from your phone to your Mac — over the same Wi-Fi.</b>
</p>

<p align="center">
  <a href="https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg">
    <img alt="Download for macOS" src="https://img.shields.io/badge/Download-macOS-black?style=for-the-badge&logo=apple">
  </a>
  <a href="LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge">
  </a>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Apple%20Silicon%20%7C%20Intel-lightgrey?style=for-the-badge">
</p>

<p align="center">
  No account. No public file host. The file never leaves your network.
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#install">Install</a> •
  <a href="#usage">Usage</a> •
  <a href="#troubleshooting">Troubleshooting</a> •
  <a href="#privacy">Privacy</a> •
  <a href="#development">Development</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Overview

SendToMac moves files, photos and short notes between a phone and a Mac on the same Wi-Fi.

The Mac app lives in the menu bar and shows a QR code plus an 8-character pairing code. Your phone scans the code and opens a transfer page in its browser — **no phone app to install**. Received files land in:

```
~/Downloads/SendToMac
```

The public website only introduces and distributes the app. Files are never uploaded to GitHub, Vercel or any other host.

### Features

| | |
|---|---|
| 📷 | QR-code pairing with a random 8-character code |
| 🖥️ | macOS menu-bar app, Apple Silicon and Intel |
| 🌐 | No phone app required — works in the phone browser |
| 📝 | Send short notes, links and addresses as well as files |
| 🔒 | No account, no analytics, no tracking cookies |
| 💾 | Pairing codes kept in memory only |
| ⚡ | Local-network transfer, one pairing at a time |

### How it works

```
 Phone                                Mac
   │                                   │
   │  1. Open the menu-bar window      │
   │     and see the QR code           │
   │                                   │
   │  2. Scan the QR code              │
   │     (same Wi-Fi network)          │
   │ ────────────────────────────────▶ │
   │                                   │
   │  3. Pick or drop a file           │
   │ ────────────────────────────────▶ │
   │                                   │
   │                       ~/Downloads/SendToMac
```

The server runs on the Mac (port `8790`) and is reachable from any device on the same network. Because a plain local page can't open a direct browser-to-browser channel, the Mac relays files between the paired devices. Temporary files are deleted once the receiving device downloads them, or after about 15 minutes if unclaimed.

## Install

**Requirements:** macOS 11 (Big Sur) or later, Apple Silicon or Intel (MacBook Air, MacBook Pro, iMac, Mac mini, …). The phone needs any modern browser.

1. Download [`SendToMac.dmg`](https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg).
2. Open it and run **Install SendToMac.command** (preferred) — it clears quarantine and copies the app to Applications. Or drag **SendToMac** to the Applications folder.
3. First launch: right-click the app → **Open**, or go to **System Settings → Privacy & Security → Open Anyway**.
4. Allow **Local Network** / incoming connections when macOS asks.

> SendToMac is not yet notarized, so macOS may block the first launch. This is expected.

**Opening the app:** click the menu-bar icon, or use **⌥ Option + ⌘ Command** (if enabled). You can turn on **Open at Login** from the icon's right-click menu.

## Usage

**Phone → Mac**

1. Scan the QR code shown by SendToMac.
2. Choose a file or photo on the phone.
3. It arrives in `~/Downloads/SendToMac`.

**Mac → Phone**

1. Pair the phone first (scan the QR code).
2. Drop a file on the SendToMac window and press **Send**, or choose **Photos or files**.
3. You can also type a note, link or address and send that.

### Limits

- One pairing at a time — a third device can't join an active session
- Maximum file size: **500 MB**
- Maximum note size: **20,000 characters**
- Android share-sheet integration isn't available yet

## Troubleshooting

| Problem | Fix |
|---|---|
| macOS says the app is damaged or can't be opened | Right-click → **Open**, or run `xattr -cr /Applications/SendToMac.app` and re-run **Install SendToMac.command** |
| The phone can't open the page | Both devices must be on the same Wi-Fi. Allow **Local Network** / incoming connections when macOS asks |
| Guest or public Wi-Fi doesn't work | Those networks often isolate clients. Join your phone's hotspot from the Mac and scan again |

## Privacy

- No account, no analytics, no tracking cookies
- Pairing codes are never written to disk
- Files stay on your local network and are saved only in `Downloads/SendToMac`
- The **⌥ + ⌘** shortcut only checks those two keys — it doesn't record or store other keystrokes

Full policy: [`web/privacy/index.html`](web/privacy/index.html), also published at `/privacy`.

## Development

**Requirements:** Python 3, `pyobjc`, `pywebview`.

```bash
python3 site.py              # run the transfer site/server from source (port 8790)
python3 site.py --self-test  # quick protocol checks — run after server changes
./scripts/test-codesign.sh   # signing, launcher layout and corner cases
```

`site.py` serves the transfer page; it does not launch the menu-bar app. The downloadable app is a windowed build of the same server plus a menu-bar shell (`menu_app.py`).

### Build a release

1. Build both apps with PyInstaller using `SendToMac.spec`: Apple Silicon into `dist/`, Intel into `dist-intel/`.
2. Run `./scripts/make-dmg.sh`. It assembles the universal app, rebuilds the launcher for macOS 11+, signs it ad-hoc and writes `dist/SendToMac.dmg`.

The DMG bundles both architectures; `launcher.c` starts whichever one matches the Mac.

### Project structure

```
sendtomac/
├── site.py                  # local server, WebSocket relay, /api/* (use this)
├── sendtomac.py             # older entry point
├── menu_app.py              # menu-bar UI (PyObjC + WKWebView)
├── staging.py               # staged uploads for the menu window
├── launcher.c               # universal launcher → nested arch app
├── SendToMac.spec           # PyInstaller config
├── Install SendToMac.command
├── scripts/                 # make-dmg, codesign, tests
├── web/                     # landing site, transfer pages, Vercel api/
├── assets/                  # logo, DMG background
└── LICENSE
```

### Architecture

| Component | Role |
|---|---|
| **Mac app** | Menu-bar window, QR code, local transfer, file saving |
| **Phone browser** | Opens the scanned transfer page — no install |
| **Local server** | Runs on the Mac, port `8790`, relays files |
| **Website** | Product, download and privacy pages |

## Roadmap

- [ ] macOS notarization
- [ ] Android share-sheet integration
- [ ] Multiple simultaneous pairings

Tracked in the [issue tracker](https://github.com/Hasninemamud/sendtomac/issues).

## Contributing

1. Open an issue first to discuss any major change.
2. Fork the repo and create a feature branch.
3. Make your change and test it locally.
4. Update the docs if needed.
5. Open a pull request with a clear description.

**Reporting a bug?** [Open an issue](https://github.com/Hasninemamud/sendtomac/issues) with your macOS version, Mac model (Apple Silicon or Intel), phone model and browser, network setup, steps to reproduce, and any error message or screenshot.

## Author

**Hasnine Mamud** — [@Hasninemamud](https://github.com/Hasninemamud)

## License

Released under the [MIT License](LICENSE).
