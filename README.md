<p align="center">
  <img src="assets/logo-source.png" alt="SendToMac" width="128">
</p>

<h1 align="center">SendToMac</h1>

<p align="center">
  <b>The easiest way to scan and transfer a file from a phone to a Mac on the same Wi-Fi.</b>
</p>

<p align="center">
  <a href="https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg">
    <img alt="Download for Mac" src="https://img.shields.io/badge/Download-macOS-black?style=for-the-badge&logo=apple">
  </a>
  <a href="LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge">
  </a>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Apple%20Silicon%20%7C%20Intel-lightgrey?style=for-the-badge">
</p>

<p align="center">
  No account. No public file host. The phone scans a code, then the file stays on that network.
</p>

Description

SendToMac is a local file-transfer application that lets you send files, photos, and short notes between a phone and a Mac while both devices are connected to the same Wi-Fi network.

The Mac application runs from the menu bar and displays a QR code and an 8-character pairing code. The phone scans the QR code using its camera and opens the transfer page in a browser. No phone application needs to be installed.

Files are transferred over the local network while the Mac application is running. Received files are saved to:

~/Downloads/SendToMac

The public website is only used to introduce and distribute the product. Files are not uploaded to GitHub, Vercel, or another public file host.

Features

📱 Transfer files between a phone and Mac over the same Wi-Fi

📷 QR-code based pairing

🔢 Random 8-character pairing code

🖥️ macOS menu-bar application

🌐 No phone application required

📁 Saves received files to Downloads/SendToMac

📝 Send short notes, links, and addresses

🔒 No account required

🚫 No analytics or tracking cookies

💾 Pairing codes are kept only in memory

🍎 Supports Apple Silicon and Intel Macs

⚡ Local network transfer

🔄 One pair at a time

How it works

Phone                              Mac
  |                                  |
  |  1. Open SendToMac               |
  |     menu-bar window              |
  |     shows a QR code              |
  |                                  |
  |  2. Scan the QR code             |
  |     on the same Wi-Fi            |
  |--------------------------------->|
  |                                  |
  |  3. Select or drop a file        |
  |--------------------------------->|
  |                                  |
  |                         Downloads/SendToMac

Pairing

Open SendToMac on the Mac.

The application displays a QR code and an 8-character pairing code.

Scan the QR code using the phone camera.

Both devices must be connected to the same Wi-Fi network.

The scan pairs the phone with the Mac.

Either side can then send a file, photo, or short note.

The pairing code is generated randomly and kept only in memory.

Installation

SendToMac supports both Apple Silicon and Intel Macs.

Download

Download the latest macOS disk image:

<a href="https://github.com/Hasninemamud/sendtomac/releases/latest/download/SendToMac.dmg">
  <img alt="Download SendToMac" src="https://img.shields.io/badge/Download-SendToMac-black?style=for-the-badge&logo=apple">
</a>

Install

Open SendToMac.dmg.

Prefer Install SendToMac.command. It clears quarantine and copies the application to Applications.

Alternatively, drag SendToMac into the Applications folder.

If macOS blocks the application, right-click it and select Open, or go to:
System Settings → Privacy & Security → Open Anyway.

Allow Local Network or incoming connections if macOS asks for permission.

SendToMac is not notarized yet, so macOS may block the application during the first launch.

Open SendToMac

You can open the application from the menu-bar icon.

If enabled, you can also use:

Option + Command

Open at Login is optional and can be enabled from the menu-bar icon's right-click menu.

Usage

Send a file from Mac

After the phone has scanned the QR code:

Drop a file onto the SendToMac window and press Send.

Or choose Photos or files.

You can also type a note, link, or address and send it.

Send a file from phone

Scan the QR code displayed by SendToMac.

Select a file or photo from the phone.

The selected item is transferred to the Mac.

Received files are stored in:

~/Downloads/SendToMac

Network requirements

Both devices must be able to communicate with each other over the local network.

Guest or public Wi-Fi networks that isolate connected devices may not work.

If necessary, connect the Mac to the phone's hotspot and scan the QR code again.

Architecture

SendToMac consists of several parts:

Component

Role

Mac app

Menu-bar window, QR code, local transfer, and file saving

Phone browser

Opens the scanned transfer page; no app installation required

Pairing code

Connects the two devices

Local server

Runs on the Mac at port 8790

Website

Product/download page and privacy information

The local server runs on the Mac and is reachable from devices on the same Wi-Fi network.

Because a plain local page cannot open a direct browser-to-browser transfer channel, the Mac relays the file between the connected devices.

Temporary files are removed after the receiving device downloads them, or after approximately 15 minutes if they remain unclaimed.

Privacy

SendToMac is designed for local transfers.

No account is required.

No analytics are included.

No tracking cookies are used.

Pairing codes are not written to disk.

Files are intended to remain on the local network.

Received files are stored locally in Downloads/SendToMac.

The Option + Command shortcut checks only those two keys and does not record or store other keystrokes.

For the full privacy policy, see:

web/privacy/index.html

The privacy page is also published at:

/privacy

Limits

One pair at a time.

A third device cannot join the same pairing session.

Maximum file size: 500 MB.

Maximum note size: 20,000 characters.

Android share-sheet integration is not currently available.

The first macOS launch may require right-click → Open because the application is not notarized.

Requirements

For users

macOS

Apple Silicon or Intel Mac

Phone with a camera and modern web browser

Both devices connected to the same Wi-Fi network

For development

The project requires:

Python 3

pyobjc

pywebview

Run from source

To run the web transfer page from source:

python3 site.py

This opens the transfer site in a browser.

Running site.py opens the transfer page; it does not launch the menu-bar application itself.

The downloadable application is a windowed build of the local server combined with a menu-bar shell.

Build-related files include:

SendToMac.spec
launcher.c

The distributed disk image contains both Apple Silicon and Intel builds. The launcher starts the build appropriate for the Mac.

Project Structure

A simplified project structure is:

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

Roadmap

Potential future improvements can be tracked through the project's issue tracker.

Current documented limitations include:

macOS notarization

Android share-sheet integration

Single-pair transfer limitation

Support

If you encounter a problem or have a feature request, open an issue in the GitHub repository:

https://github.com/Hasninemamud/sendtomac

When reporting an issue, include:

macOS version

Mac model / Apple Silicon or Intel

Phone model and browser

Network setup

Steps to reproduce the problem

Relevant error message or screenshot

Contributing

Contributions are welcome.

Before making a major change, open an issue to discuss the proposed change.

For pull requests:

Fork the repository.

Create a feature branch.

Make your changes.

Test the changes locally.

Update documentation when necessary.

Open a pull request with a clear description of the change.

Author

Hasnine Mamud

GitHub:
https://github.com/Hasninemamud

License

Released under the MIT License.
