<p align="center">
  <img src="web/logo.png" alt="SendToMac" width="128">
</p>

<h1 align="center">SendToMac</h1>

<p align="center">
  <b>The easiest way to scan and transfer a file from a phone to a Mac on the same Wi-Fi.</b>
</p>

<p align="center">
  <a href="https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg"><img alt="Download for Mac" src="https://img.shields.io/badge/Download-macOS-black?style=for-the-badge&logo=apple"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge"></a>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Apple%20Silicon%20%7C%20Intel-lightgrey?style=for-the-badge">
</p>

<p align="center">
  No account. No public file host. The phone scans a code, then the file stays on that network.
</p>

---

## How it works

```text
Phone                         Mac
  |                            |
  |  1. Open SendToMac         |
  |     menu-bar window        |
  |     shows a QR code        |
  |                            |
  |  2. Scan the QR            |
  |     (same Wi-Fi)           |
  |--------------------------->|
  |                            |
  |  3. Pick or drop a file    |
  |--------------------------->|
  |                            |
  |                     saved in Downloads/SendToMac
```

1. The Mac app opens a menu-bar window. It does not open a website, and it does not appear in the Dock.
2. The window shows a QR code and an 8-character pairing code, generated at random and kept only in memory.
3. The phone camera scans that code. Both devices must be on the same Wi-Fi — the scan only pairs them.
4. Once paired, either side can send a file, a photo, or a short note.
5. A file received in the Mac app is saved to `Downloads/SendToMac`.

The public site only explains the product. The bytes move on the local network while the Mac app is running — they are never uploaded to GitHub, Vercel, or any other public server.

---

## Install the Mac app

Works on Apple silicon and Intel — one disk image covers both.

1. Open `SendToMac.dmg`.
2. Drag **SendToMac** into **Applications**.
3. The first time, **right-click** the app and choose **Open**. It isn't an App Store app, so a normal double-click is blocked until you do this once.
4. Allow incoming connections if macOS asks — that's the phone reaching the Mac over your Wi-Fi.
5. If macOS asks for **Accessibility** access, allow it. That permission exists only so **Option + Command** can open the window — the app never records what you type.

Leave the menu-bar icon running while you send. Received files land in `Downloads/SendToMac`. Right-click the menu-bar icon and choose **Quit SendToMac** when you're done — quitting ends the pairing.

### Open it

- Press **Option + Command**, **or**
- Click the menu-bar icon.

The app must be running for the shortcut to work. It stays in the menu bar after launch and can offer to start at login so the shortcut keeps working after a restart.

### Send a file

**On the Mac**, once the phone has scanned the code:

- Drop a file onto the window, then press **Send**, **or**
- Choose **Photos or files**, **or**
- Type a note, link, or address and send that.

**On the phone**, pick a file or photo after the code connects — the other device receives it instantly.

> **Note:** Guest or public Wi-Fi that isolates devices from each other won't work. Use a normal home network, or join the phone's hotspot from the Mac and scan again.

---

## What each piece does

| Piece | Role |
|---|---|
| **Mac app** | Menu-bar window, QR code, local transfer, saves files to `Downloads/SendToMac` |
| **Phone browser** | Opens the scanned link — no app to install |
| **Pairing code** | Connects exactly two devices; anyone with the link can try to join while it's open |
| **Local server** | Runs on the Mac at port `8790` — reachable only from your Wi-Fi |
| **Website** | Download page and privacy policy — it never stores files |

On a home network, the Mac relays the file between the two devices, since a plain local page can't open a direct browser-to-browser channel. Files sit in a temporary folder only until the other device downloads them, or for about 15 minutes if left unclaimed — then they're deleted.

A public HTTPS copy of the site, if someone hosts one, only introduces the two devices to each other. The file itself is meant to travel directly between them, but a short note and the handshake do pass through that host — don't send secrets through a host you don't trust.

---

## Limits

- One pair at a time — a third device can't join the same code.
- A file can be up to **500 MB**; a note can be up to **20,000 characters**.
- Doesn't appear in the Android share sheet — the phone uses the camera and browser instead.
- First launch needs right-click **Open**, since the app isn't notarized.

---

## Privacy

No account. No analytics. No tracking cookies. Pairing codes are never written to disk.

The Option + Command shortcut only checks those two keys — it doesn't read or store any other keystrokes.

Full policy: [privacy page](web/privacy/index.html), also published on the website at `/privacy`.

---

## Run it from source

Requires **Python 3** and the packages used by the Mac app environment (`pyobjc`, `pywebview`).

```bash
python3 site.py
```

This opens the site in a browser — the same transfer page, not the menu-bar app.

The downloadable app is a windowed build of that server plus a menu-bar shell. Build notes live in `SendToMac.spec` and `launcher.c`. One disk image contains both an Apple silicon build and an Intel build; the launcher starts whichever matches the Mac.

---

## License

Released under the [MIT License](LICENSE).
