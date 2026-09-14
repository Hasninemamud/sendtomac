<p align="center">
  <img src="web/logo.png" alt="SendToMac" width="128">
</p>

<h1 align="center">SendToMac</h1>

<p align="center">The easiest way to scan and transfer a file from a phone to a Mac on the same Wi-Fi.</p>

No account. No public file host. The phone scans a code, then the file stays on that network.

[Download for Mac](https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg)

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
2. The window shows a QR code and an 8-character pairing code. The code is random and lives only in memory.
3. The phone camera opens that code. Both devices must be on the same Wi-Fi. The scan only pairs them.
4. After the pair is ready, either side can send a file, a photo, or a short note.
5. A file received in the Mac app is saved to `Downloads/SendToMac`.

The public site only explains the product. The bytes move on the local network while the Mac app is running. They are not uploaded to GitHub, Vercel, or any other public server.

## Use the Mac app

Apple silicon and Intel. One disk image covers both.

1. Open `SendToMac.dmg`.
2. Drag **SendToMac** to **Applications**.
3. The first time, right-click the app and choose **Open**. It is not an App Store app, so a normal double-click is blocked until you do that.
4. Allow incoming connections if macOS asks. That is the phone reaching the Mac on your Wi-Fi.
5. If macOS asks for Accessibility, allow SendToMac. That permission is only so Option + Command can open the window. The app does not record what you type.

Leave the menu-bar icon running while you send. Received files go to `Downloads/SendToMac`. Right-click the menu-bar icon and choose **Quit SendToMac** when you are done. Quitting ends the pair.

### Open it

- Press **Option + Command**.
- Or click the menu-bar icon.

The app has to be running for the shortcut to work. It stays in the menu bar after you open it. It also offers to start at login so the shortcut still works after a restart.

### Send a file

On the Mac window, after the phone has scanned:

- Drop a file onto the window, then press **Send**.
- Or choose **Photos or files**.
- Or type a note, link, or address and send that.

On the phone, pick a file or photo after the code connects. The other device receives it.

A guest or public Wi-Fi that hides devices from each other will not work. Use a normal home Wi-Fi, or join the phone's hotspot from the Mac and scan again.

## What each piece does

| Piece | Role |
| --- | --- |
| Mac app | Menu-bar window, QR code, local transfer, saves files to `Downloads/SendToMac` |
| Phone browser | Opens the scanned link. No app to install |
| Pairing code | Connects exactly two devices. Anyone with the link can try to join while it is open |
| Local server | Runs on the Mac, port `8790`. Only your Wi-Fi can reach it |
| Website | Download page and privacy policy. It does not store files |

On a home network the Mac relays the file between the two devices, because a plain local page cannot open a direct browser-to-browser channel. The file is kept in a temporary folder only until the other device downloads it, or for about 15 minutes if it is not downloaded. Then it is deleted.

A public HTTPS copy of the site, if someone hosts one, only introduces the two devices. The file is meant to go directly between them. A short note and the handshake do pass through that host. Do not send secrets through a host you do not trust.

## Limits

- One pair at a time. A third device cannot join the same code.
- A file can be up to 500 MB. A note can be up to 20,000 characters.
- This does not appear in the Android share sheet. The phone uses the camera and the browser.
- The first launch needs right-click **Open**. The app is not notarized.

## Privacy

No account. No analytics. No tracking cookies. Pairing codes are not written to disk.

The Option + Command shortcut only checks those two keys. It does not read or store other keystrokes.

Full policy: [privacy page](web/privacy/index.html), also on the website at `/privacy`.

## Run it from source

Requires Python 3 and the packages in the Mac app environment (`pyobjc`, `pywebview`).

```bash
python3 site.py
```

That opens the site in a browser. It is the same transfer page, not the menu-bar app.

The downloadable app is a windowed build of that server plus a menu-bar shell. Build notes live in `SendToMac.spec` and `launcher.c`. One disk image contains an Apple silicon build and an Intel build. The launcher starts the one that matches the Mac.
