<p align="center">
  <img src="assets/logo-source.png" alt="SendToMac logo" width="128">
</p>

<h1 align="center">SendToMac</h1>

<p align="center">
  <b>The easiest way to scan and transfer a file from your phone to your Mac — over the same Wi-Fi.</b>
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
  No account. No public file host. Your phone scans a code, and the file never leaves your network.
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#how-it-works">How it works</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#privacy">Privacy</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Overview

SendToMac is a local file-transfer app that lets you send files, photos, and short notes between a phone and a Mac while both devices sit on the same Wi-Fi network.

The Mac app lives in the menu bar and shows a QR code plus an 8-character pairing code. Your phone scans the code and opens a transfer page in its browser — no app install required. Everything moves over your local network, and received files land in:

```
~/Downloads/SendToMac
```

The public website exists only to introduce and distribute the product. Files are never uploaded to GitHub, Vercel, or any public file host.

## Features

| | |
|---|---|
| 📱 | Transfer files between phone and Mac over the same Wi-Fi |
| 📷 | QR-code based pairing |
| 🔢 | Random 8-character pairing code |
| 🖥️ | macOS menu-bar app |
| 🌐 | No phone app required |
| 📁 | Saves received files to `Downloads/SendToMac` |
| 📝 | Send short notes, links, and addresses |
| 🔒 | No account required |
| 🚫 | No analytics or tracking cookies |
| 💾 | Pairing codes kept in memory only |
| 🍎 | Supports Apple Silicon and Intel Macs |
| ⚡ | Local network transfer |
| 🔄 | One pairing at a time |

## How it works

```
 Phone                                Mac
   │                                   │
   │  1. Open SendToMac's menu-bar     │
   │     window — see the QR code      │
   │                                   │
   │  2. Scan the QR code              │
   │     (same Wi-Fi network)          │
   │ ────────────────────────────────▶ │
   │                                   │
   │  3. Select or drop a file         │
   │ ────────────────────────────────▶ │
   │                                   │
   │                       ~/Downloads/SendToMac
```

### Pairing

1. Open **SendToMac** on the Mac.
2. It displays a QR code and an 8-character pairing code.
3. Scan the QR code with your phone's camera.
4. Both devices must be on the same Wi-Fi network — the scan pairs them.
5. Either side can now send a file, photo, or short note.

The pairing code is generated randomly and kept only in memory — never written to disk.

## Installation

SendToMac supports both Apple Silicon and Intel Macs.

### Download

<a href="https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg">
  <img alt="Download SendToMac" src="https://img.shields.io/badge/Download-SendToMac.dmg-black?style=for-the-badge&logo=apple">
</a>

### Install

1. Open `SendToMac.dmg`.
2. Run **Install SendToMac.command** (preferred) — it clears quarantine and copies the app to Applications.
   - Alternatively, drag **SendToMac** into the Applications folder.
3. If macOS blocks the app: right-click it → **Open**, or go to **System Settings → Privacy & Security → Open Anyway**.
4. Allow **Local Network** or incoming-connection permissions if macOS prompts for them.

> **Note:** SendToMac is not yet notarized, so macOS may block it on first launch — this is expected.

### Opening the app

- Click the menu-bar icon, or
- Use the shortcut **⌥ Option + ⌘ Command** (if enabled)
- Enable **Open at Login** from the menu-bar icon's right-click menu (optional)

## Usage

### Send a file from your Mac

Once your phone has scanned the QR code:

- Drop a file onto the SendToMac window and press **Send**, or
- Choose **Photos or files**
- You can also type a note, link, or address and send it

### Send a file from your phone

1. Scan the QR code shown by SendToMac.
2. Select a file or photo on your phone.
3. It transfers to the Mac and lands in `~/Downloads/SendToMac`.

### Network requirements

- Both devices must be able to reach each other on the local network.
- Guest / public Wi-Fi networks with client isolation may not work.
- If needed, connect the Mac to your phone's hotspot and scan again.

## Architecture

| Component | Role |
|---|---|
| **Mac app** | Menu-bar window, QR code, local transfer, file saving |
| **Phone browser** | Opens the scanned transfer page — no install needed |
| **Pairing code** | Connects the two devices |
| **Local server** | Runs on the Mac, port `8790` |
| **Website** | Product/download page and privacy info |

The local server runs on the Mac and is reachable from any device on the same Wi-Fi network. Since a plain local page can't open a direct browser-to-browser channel, the Mac relays files between the connected devices. Temporary files are deleted once the receiving device downloads them, or after roughly 15 minutes if unclaimed.

## Privacy

- No account required
- No analytics, no tracking cookies
- Pairing codes are never written to disk
- Files stay on the local network
- Received files are stored locally in `Downloads/SendToMac`
- The `⌥ + ⌘` shortcut only checks those two keys — it doesn't record or store other keystrokes

Full privacy policy: [`web/privacy/index.html`](web/privacy/index.html) · Also published at `/privacy`

## Limits

- One pairing at a time — a third device can't join an active session
- Maximum file size: **500 MB**
- Maximum note size: **20,000 characters**
- Android share-sheet integration isn't available yet
- First launch may require right-click → Open (app isn't notarized)

## Development

**Requirements**

- Python 3
- `pyobjc`
- `pywebview`

**Run the transfer page from source**

```bash
python3 site.py
```

This opens the transfer site in a browser. It does *not* launch the menu-bar app itself — the downloadable app is a windowed build of the local server combined with a menu-bar shell.

**Build-related files**

- `SendToMac.spec`
- `launcher.c`

The distributed disk image bundles both Apple Silicon and Intel builds; the launcher starts whichever matches the Mac.

### Project structure

```
SendToMac/
├── assets/
│   └── logo-source.png
├── web/
│   └── privacy/
│       └── index.html
├── site.py
├── SendToMac.spec
├── launcher.c
├── LICENSE
└── README.md
```

## Roadmap

Tracked via the [issue tracker](https://github.com/Hasninemamud/sendtomac/issues). Currently documented limitations:

- [ ] macOS notarization
- [ ] Android share-sheet integration
- [ ] Multi-device / simultaneous pairing

## Support

Found a bug or have a feature request? [Open an issue](https://github.com/Hasninemamud/sendtomac/issues) and include:

- macOS version
- Mac model (Apple Silicon or Intel)
- Phone model and browser
- Network setup
- Steps to reproduce
- Relevant error message or screenshot

## Contributing

Contributions are welcome!

1. Open an issue first to discuss any major change.
2. Fork the repository.
3. Create a feature branch.
4. Make your changes and test locally.
5. Update documentation when necessary.
6. Open a pull request with a clear description.

## Author

**Hasnine Mamud**
GitHub: [@Hasninemamud](https://github.com/Hasninemamud)

## License

Released under the [MIT License](LICENSE).
