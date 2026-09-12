#!/usr/bin/env python3
"""SendToMac — Android share that lands in the right place on the Mac.

No Android app, no account, no cloud. Pair once by QR (or a code). Text is
copied to the Mac clipboard, a lone link opens, files are revealed in Finder.
Works when mDNS discovery is blocked, which is what breaks LocalSend and
KDE Connect on many networks.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import zlib
import struct
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
VENDOR = ROOT / "vendor"
HOME = Path.home() / ".sendtomac"
CONFIG_PATH = HOME / "config.json"
INBOX_PATH = HOME / "inbox.json"
LOG_PATH = HOME / "sendtomac.log"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "local.sendtomac.plist"
SAVE_DIR = Path.home() / "Downloads" / "SendToMac"
DEFAULT_PORT = 8787
MAX_BYTES = 800 * 1024 * 1024
MAX_TEXT = 100_000
CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
APP = "sendtomac"

DEFAULT_PREFS = {
    "copyText": True,
    "openLinks": True,
    "revealFiles": True,
    "copyImages": True,
    "sound": True,
    "pasteFront": False,
}

LOCK = threading.Lock()
SHARE_LOCK = threading.Lock()
STATE: dict = {}


def codes_match(code: str) -> bool:
    expected = str(STATE["config"]["code"])
    if not isinstance(code, str) or len(code) != len(expected):
        return False
    return secrets.compare_digest(code, expected)


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback


def save_json(path: Path, data) -> None:
    HOME.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def pairing_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def ensure_config() -> dict:
    HOME.mkdir(mode=0o700, exist_ok=True)
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_json(CONFIG_PATH, {})
    if not re.fullmatch(r"[a-z0-9]{6,12}", str(cfg.get("code", ""))):
        cfg["code"] = pairing_code()
    prefs = dict(DEFAULT_PREFS)
    prefs.update(cfg.get("prefs") or {})
    cfg["prefs"] = {k: bool(prefs.get(k)) for k in DEFAULT_PREFS}
    save_json(CONFIG_PATH, cfg)
    return cfg


def computer_name() -> str:
    try:
        name = subprocess.check_output(
            ["scutil", "--get", "ComputerName"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if name:
            return name
    except (OSError, subprocess.CalledProcessError):
        pass
    return socket.gethostname() or "Mac"


def lan_ips() -> list[str]:
    found: list[str] = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."):
            found.append(ip)
    except OSError:
        pass
    try:
        out = subprocess.check_output(["ifconfig"], text=True, errors="replace")
    except (OSError, subprocess.CalledProcessError):
        return found
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "inet":
            ip = parts[1]
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue
            if ip not in found:
                found.append(ip)
    return found


def phone_url(port: int, code: str) -> str | None:
    ips = lan_ips()
    if not ips:
        return None
    return f"http://{ips[0]}:{port}/m/{code}"


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(title: str, body: str) -> None:
    script = (
        f"display notification {applescript_string(body[:180])} "
        f"with title {applescript_string(title[:60])}"
    )
    subprocess.run(["osascript", "-e", script], check=False)


def copy_text(value: str) -> None:
    subprocess.run(["pbcopy"], input=value.encode(), check=False)


def copy_image(path: Path, mime: str) -> None:
    kinds = {
        "image/png": "«class PNGf»",
        "image/jpeg": "«class JPEG»",
        "image/gif": "«class GIFf»",
        "image/tiff": "«class TIFF»",
    }
    kind = kinds.get(mime)
    if not kind:
        return
    script = (
        f"set the clipboard to (read (POSIX file {applescript_string(str(path))}) as {kind})"
    )
    subprocess.run(["osascript", "-e", script], check=False)


def paste_front() -> None:
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to keystroke "v" using command down',
        ],
        check=False,
    )


def play_sound() -> None:
    sound = "/System/Library/Sounds/Glass.aiff"
    if os.path.exists(sound):
        subprocess.Popen(
            ["afplay", sound],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def safe_name(name: str) -> str:
    name = os.path.basename(name or "").replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name or name in {".", ".."}:
        name = "file"
    return name[:120]


def unique_path(filename: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = safe_name(filename)
    stem, dot, ext = base.rpartition(".")
    if not stem:
        stem, ext = base, ""
    candidate = SAVE_DIR / f"{stamp}-{base}"
    n = 2
    while candidate.exists():
        suffix = f".{ext}" if ext and dot else ""
        plain = stem if dot else base
        candidate = SAVE_DIR / f"{stamp}-{plain}-{n}{suffix}"
        n += 1
    return candidate


def under_save(path: str) -> bool:
    root = os.path.realpath(SAVE_DIR)
    target = os.path.realpath(path)
    return target == root or target.startswith(root + os.sep)


def classify(text: str) -> tuple[str, str]:
    raw = text.strip()
    if not raw or "\n" in raw or len(raw) > 2000:
        return "text", raw
    cleaned = raw.rstrip(").,;")
    if re.fullmatch(r"https?://\S+", cleaned):
        return "url", cleaned
    if re.fullmatch(r"mailto:\S+", cleaned, re.I):
        return "url", cleaned
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
        return "url", "mailto:" + cleaned
    return "text", raw


def inbox_add(item: dict) -> None:
    with LOCK:
        data = load_json(INBOX_PATH, {"items": []})
        items = data.get("items") or []
        items.insert(0, item)
        data["items"] = items[:200]
        save_json(INBOX_PATH, data)


def find_item(item_id: str) -> dict | None:
    data = load_json(INBOX_PATH, {"items": []})
    for item in data.get("items") or []:
        if item.get("id") == item_id:
            return item
    return None


IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".heic": "image/heic",
}


def mime_for(name: str, claimed: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in IMAGE_MIME:
        return IMAGE_MIME[ext]
    claimed = (claimed or "").split(";")[0].strip().lower()
    return claimed or "application/octet-stream"


def receive(text: str, files: list[dict], prefs: dict) -> dict:
    text = (text or "")[:MAX_TEXT]
    saved = []
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    for incoming in files:
        path = unique_path(incoming.get("filename") or "file")
        path.write_bytes(incoming.get("data") or b"")
        os.chmod(path, 0o644)
        saved.append(
            {
                "name": path.name,
                "path": str(path),
                "size": path.stat().st_size,
                "mime": mime_for(path.name, incoming.get("mime") or ""),
            }
        )

    kind, payload = classify(text) if text.strip() else ("", "")
    bits = []
    if payload and prefs.get("copyText", True):
        copy_text(payload if kind == "url" else text.strip())
        bits.append("Copied to the clipboard")
    if kind == "url" and prefs.get("openLinks", True):
        subprocess.run(["open", payload], check=False)
        bits.append("opened")
    if prefs.get("pasteFront") and text.strip() and not saved:
        paste_front()
        bits.append("pasted into the front app")
    if saved and prefs.get("revealFiles", True):
        subprocess.run(["open", "-R", saved[0]["path"]], check=False)
        bits.append("shown in Finder")
    if (
        len(saved) == 1
        and saved[0]["mime"] in {"image/png", "image/jpeg", "image/gif", "image/tiff"}
        and prefs.get("copyImages", True)
    ):
        copy_image(Path(saved[0]["path"]), saved[0]["mime"])
        bits.append("photo is on the clipboard")

    if not bits and not saved and not text.strip():
        raise ValueError("Nothing to send")

    if saved and not bits:
        bits.append(f"Saved {len(saved)} file" + ("s" if len(saved) != 1 else ""))
    if text.strip() and not bits:
        bits.append("Received")

    summary = ". ".join(bits)
    if saved:
        names = ", ".join(item["name"] for item in saved[:3])
        extra = "" if len(saved) <= 3 else f" +{len(saved) - 3}"
        summary = f"{summary}. {names}{extra}"
    elif text.strip() and kind != "url":
        preview = text.strip().replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "…"
        summary = f"{summary}. {preview}"
    elif kind == "url":
        summary = f"{summary}. {payload}"

    item = {
        "id": secrets.token_hex(8),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": summary,
        "text": text.strip(),
        "files": saved,
    }
    inbox_add(item)
    notify("From your phone", summary)
    if prefs.get("sound", True):
        play_sound()
    return {"ok": True, "summary": summary, "id": item["id"]}


def disp_param(header: str, key: str) -> str | None:
    match = re.search(rf'{key}="([^"]*)"', header, re.I)
    if match:
        return match.group(1)
    match = re.search(rf"{key}=([^;]+)", header, re.I)
    if match:
        return match.group(1).strip().strip('"')
    return None


def parse_multipart(content_type: str, body: bytes) -> tuple[dict, list]:
    match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type, re.I)
    if not match:
        raise ValueError("Missing upload boundary")
    boundary = (match.group(1) or match.group(2)).strip()
    marker = b"--" + boundary.encode("ascii", "strict")
    fields: dict[str, str] = {}
    files: list[dict] = []
    for chunk in body.split(marker):
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        elif chunk.startswith(b"\n"):
            chunk = chunk[1:]
        if not chunk or chunk.startswith(b"--"):
            continue
        sep = b"\r\n\r\n" if b"\r\n\r\n" in chunk else b"\n\n"
        if sep not in chunk:
            continue
        head, data = chunk.split(sep, 1)
        if data.endswith(b"\r\n"):
            data = data[:-2]
        elif data.endswith(b"\n"):
            data = data[:-1]
        headers = {}
        for line in head.decode("utf-8", "replace").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        disposition = headers.get("content-disposition", "")
        if "form-data" not in disposition.lower():
            continue
        name = disp_param(disposition, "name") or ""
        filename = disp_param(disposition, "filename")
        if filename is not None:
            files.append(
                {
                    "filename": filename,
                    "mime": headers.get("content-type", "application/octet-stream"),
                    "data": data,
                }
            )
        elif name:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


def icon_png(size: int = 192) -> bytes:
    bg = (28, 25, 23)
    fg = (239, 236, 230)
    raw = bytearray()
    cx = size // 2
    for y in range(size):
        raw.append(0)
        for x in range(size):
            # Down arrow into a tray.
            shaft = abs(x - cx) <= 11 and 48 <= y <= 104
            head = 88 <= y <= 122 and abs(x - cx) <= (122 - y)
            tray = 132 <= y <= 144 and 52 <= x <= size - 52
            color = fg if shaft or head or tray else bg
            raw.extend(color)
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


ICON = icon_png()


def login_item_installed() -> bool:
    return PLIST_PATH.exists()


def write_login_item(enable: bool) -> str:
    if not enable:
        if PLIST_PATH.exists():
            PLIST_PATH.unlink()
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}/local.sendtomac"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "It will no longer start at login. This window keeps running until you quit."
    HOME.mkdir(mode=0o700, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    script = xml_escape(str(ROOT / "sendtomac.py"))
    exe = xml_escape(sys.executable)
    log = xml_escape(str(LOG_PATH))
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>local.sendtomac</string>
  <key>ProgramArguments</key>
  <array>
    <string>{exe}</string>
    <string>{script}</string>
    <string>--quiet</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""
    PLIST_PATH.write_text(plist)
    return "Saved. It starts the next time you log in. Leave this window open until then."


def ping_port(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=0.4) as res:
            body = res.read()
        return b'"app":"sendtomac"' in body
    except (OSError, urllib.error.URLError):
        return False


def running_port() -> int | None:
    cfg = load_json(CONFIG_PATH, {})
    candidates = []
    if isinstance(cfg.get("port"), int):
        candidates.append(cfg["port"])
    if DEFAULT_PORT not in candidates:
        candidates.append(DEFAULT_PORT)
    for port in candidates:
        if ping_port(port):
            return port
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "SendToMac/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def local(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def send_bytes(self, code: int, body: bytes, content_type: str, cache: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code: int, payload) -> None:
        self.send_bytes(code, json.dumps(payload).encode(), "application/json; charset=utf-8")

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_json(404, {"ok": False, "error": "Missing page"})
            return
        self.send_bytes(200, path.read_bytes(), content_type)

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length < 0 or length > MAX_BYTES:
            raise ValueError("Upload is too large")
        return self.rfile.read(length)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/api/ping":
            self.send_json(200, {"ok": True, "app": APP})
            return
        if path == "/icon-192.png" or path == "/apple-touch-icon.png" or path == "/favicon.ico":
            self.send_bytes(200, ICON, "image/png", cache=True)
            return
        if path == "/vendor/qrcode.js":
            self.send_file(VENDOR / "qrcode.js", "text/javascript; charset=utf-8")
            return
        if path == "/api/bootstrap":
            if not self.local():
                self.send_json(403, {"ok": False, "error": "Mac only"})
                return
            cfg = STATE["config"]
            port = STATE["port"]
            url = phone_url(port, cfg["code"])
            self.send_json(
                200,
                {
                    "name": computer_name(),
                    "code": cfg["code"],
                    "port": port,
                    "primaryUrl": url,
                    "prefs": cfg["prefs"],
                    "loginItem": login_item_installed(),
                    "saveDir": str(SAVE_DIR),
                },
            )
            return
        if path == "/api/inbox":
            if not self.local():
                self.send_json(403, {"ok": False, "error": "Mac only"})
                return
            self.send_json(200, load_json(INBOX_PATH, {"items": []}))
            return
        if path == "/api/peer":
            code = (query.get("code") or [""])[0]
            if not codes_match(code):
                self.send_json(404, {"ok": False, "error": "Wrong pairing code"})
                return
            self.send_json(200, {"name": computer_name()})
            return
        if path.startswith("/m/") and path.endswith("/manifest.webmanifest"):
            code = path.split("/")[2]
            if not codes_match(code):
                self.send_json(404, {"ok": False, "error": "Wrong pairing code"})
                return
            manifest = {
                "name": "Send to " + computer_name(),
                "short_name": "Send to Mac",
                "start_url": f"/m/{code}",
                "display": "standalone",
                "background_color": "#efece6",
                "theme_color": "#1c1917",
                "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}],
            }
            self.send_json(200, manifest)
            return
        if path.startswith("/m/"):
            code = path.strip("/").split("/", 1)[1]
            if "/" in code or not codes_match(code):
                self.send_bytes(
                    404,
                    b"That code does not match this Mac. Scan the QR again.",
                    "text/plain; charset=utf-8",
                )
                return
            self.send_file(WEB / "phone.html", "text/html; charset=utf-8")
            return
        if path == "/":
            page = WEB / "mac.html" if self.local() else WEB / "join.html"
            self.send_file(page, "text/html; charset=utf-8")
            return
        self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/api/share":
                self.handle_share()
                return
            if not self.local():
                self.send_json(403, {"ok": False, "error": "Mac only"})
                return
            body = self.read_body()
            data = json.loads(body.decode() or "{}") if body else {}
            if parsed.path == "/api/prefs":
                prefs = STATE["config"]["prefs"]
                for key in DEFAULT_PREFS:
                    if key in data:
                        prefs[key] = bool(data[key])
                save_json(CONFIG_PATH, STATE["config"])
                self.send_json(200, {"ok": True, "prefs": prefs})
                return
            if parsed.path == "/api/item":
                self.handle_item(data)
                return
            if parsed.path == "/api/login-item":
                enable = not login_item_installed()
                message = write_login_item(enable)
                self.send_json(200, {"ok": True, "loginItem": login_item_installed(), "message": message})
                return
            if parsed.path == "/api/shutdown":
                self.send_json(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            self.send_json(404, {"ok": False, "error": "Not found"})
        except ValueError as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        except json.JSONDecodeError:
            self.send_json(400, {"ok": False, "error": "Bad JSON"})

    def handle_share(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        body = self.read_body()
        if content_type.startswith("application/json"):
            data = json.loads(body.decode() or "{}")
            fields = {"code": str(data.get("code") or ""), "text": str(data.get("text") or "")}
            files = []
        elif "multipart/form-data" in content_type:
            fields, files = parse_multipart(content_type, body)
        else:
            raise ValueError("Send text or files")
        code = fields.get("code") or ""
        if not codes_match(code):
            self.send_json(401, {"ok": False, "error": "Pairing expired. Scan the QR on the Mac again."})
            return
        with SHARE_LOCK:
            result = receive(fields.get("text") or "", files, STATE["config"]["prefs"])
        self.send_json(200, result)

    def handle_item(self, data: dict) -> None:
        item = find_item(str(data.get("id") or ""))
        if not item:
            self.send_json(404, {"ok": False, "error": "Not in the inbox"})
            return
        action = data.get("action")
        if action == "copy":
            copy_text(item.get("text") or "")
            self.send_json(200, {"ok": True})
            return
        files = item.get("files") or []
        if not files:
            self.send_json(400, {"ok": False, "error": "No file on that item"})
            return
        path = files[0]["path"]
        if not under_save(path):
            self.send_json(400, {"ok": False, "error": "Refusing that path"})
            return
        if action == "reveal":
            subprocess.run(["open", "-R", path], check=False)
        elif action == "open":
            subprocess.run(["open", path], check=False)
        else:
            raise ValueError("Unknown action")
        self.send_json(200, {"ok": True})


def serve(port: int) -> ThreadingHTTPServer:
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError:
        httpd = None
        for candidate in range(port, port + 12):
            try:
                httpd = ThreadingHTTPServer(("0.0.0.0", candidate), Handler)
                port = candidate
                break
            except OSError:
                continue
        if httpd is None:
            raise SystemExit("No free port near 8787")
    STATE["port"] = port
    STATE["config"]["port"] = port
    save_json(CONFIG_PATH, STATE["config"])
    return httpd


def main() -> None:
    quiet = "--quiet" in sys.argv
    daemon = "--daemon" in sys.argv
    no_open = "--no-open" in sys.argv or quiet
    if "--self-test" in sys.argv:
        run_self_test()
        return

    cfg = ensure_config()
    STATE["config"] = cfg
    existing = running_port()
    if existing:
        url = f"http://127.0.0.1:{existing}/"
        if not no_open:
            webbrowser.open(url)
        print(f"Already running at {url}")
        return

    if daemon:
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid > 0:
            os.close(write_fd)
            status = os.read(read_fd, 200).decode()
            if status.startswith("ok"):
                port = int(status.split()[1])
                if not no_open:
                    webbrowser.open(f"http://127.0.0.1:{port}/")
                return
            print(status or "Failed to start", file=sys.stderr)
            raise SystemExit(1)
        os.close(read_fd)
        os.setsid()
        HOME.mkdir(mode=0o700, exist_ok=True)
        log = open(LOG_PATH, "a", buffering=1)
        os.dup2(log.fileno(), 1)
        os.dup2(log.fileno(), 2)
        try:
            httpd = serve(DEFAULT_PORT)
        except SystemExit as exc:
            os.write(write_fd, f"err {exc}\n".encode())
            raise
        os.write(write_fd, f"ok {STATE['port']}\n".encode())
        os.close(write_fd)
        print(f"SendToMac listening on {STATE['port']}")
        httpd.serve_forever()
        return

    httpd = serve(DEFAULT_PORT)
    port = STATE["port"]
    url = phone_url(port, cfg["code"])
    print(f"SendToMac is running.", flush=True)
    print(f"Mac page: http://127.0.0.1:{port}/", flush=True)
    print(f"Phone:    {url or 'no Wi-Fi address found'}", flush=True)
    print("Allow incoming connections if macOS asks. Quit from the Mac page, or press Ctrl+C.", flush=True)
    if not no_open:
        webbrowser.open(f"http://127.0.0.1:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def run_self_test() -> None:
    body = (
        b"--bound\r\n"
        b'Content-Disposition: form-data; name="code"\r\n\r\n'
        b"abc\r\n"
        b"--bound\r\n"
        b'Content-Disposition: form-data; name="file"; filename="a b.jpg"\r\n'
        b"Content-Type: image/jpeg\r\n\r\n"
        b"\xff\xd8hi\r\n"
        b"--bound--\r\n"
    )
    fields, files = parse_multipart("multipart/form-data; boundary=bound", body)
    assert fields["code"] == "abc", fields
    assert files[0]["filename"] == "a b.jpg"
    assert files[0]["data"] == b"\xff\xd8hi"
    assert safe_name("../etc/passwd") == "passwd"
    assert classify("https://example.com.")[0] == "url"
    assert classify("notes")[0] == "text"
    assert classify("a@b.co") == ("url", "mailto:a@b.co")
    png = icon_png(32)
    assert png.startswith(b"\x89PNG")
    print("self-test ok")


if __name__ == "__main__":
    main()
