# SendToMac

Android → Mac without a second app, an account, or working device discovery.

LocalSend, KDE Connect, NearDrop, and Quick Share already move files. They still miss the AirDrop-like landing: text on the Mac clipboard, a link opened, a photo you can paste, a file revealed in Finder — paired by QR so guest Wi-Fi that blocks mDNS does not matter.

## Website

Both devices open the page on the same Wi-Fi. The Mac shows a QR. The phone scans it and picks a file. Nothing is installed.

```bash
python3 site.py
```

On this Mac the page is served locally, so the file never leaves the Wi-Fi. A public HTTPS copy only pairs the two devices; the file goes directly between them (`SENDTOMAC_PUBLIC=1`).

## Local receiver

`python3 sendtomac.py` is the older Mac inbox. It copies text to the clipboard and shows files in Finder. The website above is the one to use.

## Not this

It will not appear inside every Android app’s share sheet. That needs an installed app, and Android will not register a local web share target over plain HTTP. A future share-sheet app can `POST` multipart `code`, `text`, and `file` to `/api/share` on this receiver.
