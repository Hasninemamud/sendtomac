#!/usr/bin/env python3
"""SendToMac website.

Open the page on the Mac and the phone, both on the same Wi-Fi. Scan the QR,
pick a file. On a home network the bytes stay on that Wi-Fi.

HTTP (this Mac serving the page): the Mac passes the file to the phone.
HTTPS (a public site): the page only introduces the two devices. The file
moves directly between them and is not stored on the server.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def app_root() -> Path:
    if getattr(sys, "frozen", False):
        resources = Path(sys.executable).resolve().parent.parent / "Resources"
        if (resources / "web").is_dir():
            return resources
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


ROOT = app_root()
PAGE = ROOT / "web" / "share" / "index.html"
LANDING = ROOT / "web" / "index.html"
PRIVACY = ROOT / "web" / "privacy" / "index.html"
ICONS = {
    "/icon.svg": (ROOT / "web" / "icon.svg", "image/svg+xml"),
    "/icon-192.png": (ROOT / "web" / "icon-192.png", "image/png"),
    "/icon-512.png": (ROOT / "web" / "icon-512.png", "image/png"),
    "/apple-touch-icon.png": (ROOT / "web" / "apple-touch-icon.png", "image/png"),
    "/favicon.ico": (ROOT / "web" / "favicon.ico", "image/x-icon"),
    "/logo.png": (ROOT / "web" / "logo.png", "image/png"),
    "/menu-icon.png": (ROOT / "web" / "menu-icon.png", "image/png"),
    "/menu-icon-light.png": (ROOT / "web" / "menu-icon-light.png", "image/png"),
    "/menu-ink.png": (ROOT / "web" / "menu-ink.png", "image/png"),
    "/menu-bars.png": (ROOT / "web" / "menu-bars.png", "image/png"),
    "/macbook.png": (ROOT / "web" / "macbook.png", "image/png"),
}
VENDOR = ROOT / "web" / "vendor" / "qrcode.js"
PORT = 8790
PUBLIC = os.environ.get("SENDTOMAC_PUBLIC") == "1"
MAX_FILE = 500 * 1024 * 1024
MAX_TEXT = 20_000
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
TEMP = Path(tempfile.gettempdir()) / "sendtomac-site"

LOCK = threading.Lock()
ROOMS: dict[str, dict] = {}
FILES: dict[str, dict] = {}
TOKEN_PEER: dict[str, tuple[str, str]] = {}


def room_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(8))


def lan_ip() -> str | None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return None


def share_base(host_header: str, port: int) -> str | None:
    host = (host_header or "").split(",")[0].strip()
    hostname = host.split(":")[0]
    if hostname and hostname not in {"localhost", "127.0.0.1", "::1"}:
        scheme = "https" if PUBLIC else "http"
        return f"{scheme}://{host}"
    ip = lan_ip()
    if not ip:
        return None
    return f"http://{ip}:{port}"


def transfer_mode() -> str:
    return "webrtc" if PUBLIC else "relay"


def safe_name(name: str) -> str:
    name = os.path.basename(name or "").replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "file")[:120]


def ws_accept(key: str) -> str:
    import base64

    digest = hashlib.sha1((key + WS_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


def read_exact(rfile, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = rfile.read(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def read_frame(rfile) -> tuple[int, bytes] | None:
    try:
        hdr = read_exact(rfile, 2)
    except ConnectionError:
        return None
    opcode = hdr[0] & 0x0F
    length = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", read_exact(rfile, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read_exact(rfile, 8))[0]
    if length > 256 * 1024:
        raise ValueError("signaling message too large")
    mask = read_exact(rfile, 4) if hdr[1] & 0x80 else None
    data = read_exact(rfile, length) if length else b""
    if mask:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return opcode, data


def write_frame(wfile, opcode: int, data: bytes = b"") -> None:
    header = bytearray([0x80 | opcode])
    n = len(data)
    if n < 126:
        header.append(n)
    elif n < 65536:
        header.append(126)
        header += struct.pack("!H", n)
    else:
        header.append(127)
        header += struct.pack("!Q", n)
    wfile.write(bytes(header) + data)
    wfile.flush()


def send_json(peer: dict, payload: dict) -> None:
    raw = json.dumps(payload).encode()
    with peer["lock"]:
        write_frame(peer["wfile"], 1, raw)


def other_peers(room: dict, peer_id: str) -> list[dict]:
    with LOCK:
        return [p for pid, p in room["peers"].items() if pid != peer_id and p.get("wfile")]


def drop_peer(room_id: str, peer_id: str) -> None:
    notify = []
    with LOCK:
        room = ROOMS.get(room_id)
        if not room or peer_id not in room["peers"]:
            return
        peer = room["peers"].pop(peer_id)
        TOKEN_PEER.pop(peer.get("token", ""), None)
        notify = list(room["peers"].values())
        if not room["peers"]:
            ROOMS.pop(room_id, None)
    for other in notify:
        try:
            send_json(other, {"type": "left"})
        except (OSError, ValueError):
            pass


def new_peer(wfile) -> dict:
    return {
        "id": secrets.token_hex(4),
        "token": secrets.token_urlsafe(18),
        "wfile": wfile,
        "lock": threading.Lock(),
    }


def ensure_room(room_id: str | None) -> dict:
    with LOCK:
        if room_id and room_id in ROOMS:
            return ROOMS[room_id]
        room_id = room_id if room_id and re.fullmatch(r"[a-z0-9]{8}", room_id) else room_code()
        while room_id in ROOMS:
            room_id = room_code()
        room = {"id": room_id, "mode": transfer_mode(), "peers": {}}
        ROOMS[room_id] = room
        return room


def add_peer(room: dict, peer: dict) -> str | None:
    with LOCK:
        if peer["id"] in room["peers"]:
            old = room["peers"][peer["id"]]
            TOKEN_PEER.pop(old.get("token", ""), None)
        elif len(room["peers"]) >= 2:
            return "full"
        room["peers"][peer["id"]] = peer
        TOKEN_PEER[peer["token"]] = (room["id"], peer["id"])
        return None


def lookup_token(token: str) -> tuple[dict, dict] | None:
    with LOCK:
        found = TOKEN_PEER.get(token)
        if not found:
            return None
        room_id, peer_id = found
        room = ROOMS.get(room_id)
        if not room or peer_id not in room["peers"]:
            return None
        return room, room["peers"][peer_id]


def store_upload(token: str, filename: str, mime: str, data: bytes) -> dict:
    found = lookup_token(token)
    if not found:
        raise PermissionError("Not paired")
    room, peer = found
    if room["mode"] != "relay":
        raise PermissionError("This site does not store files")
    others = other_peers(room, peer["id"])
    if not others:
        raise ValueError("The other device is not connected")
    TEMP.mkdir(parents=True, exist_ok=True)
    file_id = secrets.token_urlsafe(16)
    path = TEMP / file_id
    path.write_bytes(data)
    meta = {
        "id": file_id,
        "name": safe_name(filename),
        "mime": mime if mime and not mime.startswith("text/html") else "application/octet-stream",
        "size": len(data),
        "path": str(path),
        "for": others[0]["id"],
        "at": time.time(),
    }
    with LOCK:
        FILES[file_id] = meta
    send_json(others[0], {"type": "file", "id": file_id, "name": meta["name"], "size": meta["size"]})
    return {"ok": True, "id": file_id, "name": meta["name"]}


def take_file(file_id: str, token: str) -> dict | None:
    found = lookup_token(token)
    if not found:
        return None
    _, peer = found
    with LOCK:
        meta = FILES.get(file_id)
        if not meta or meta["for"] != peer["id"]:
            return None
        return meta


def purge() -> None:
    while True:
        time.sleep(60)
        cutoff = time.time() - 15 * 60
        with LOCK:
            stale = [fid for fid, meta in FILES.items() if meta["at"] < cutoff]
            for fid in stale:
                path = FILES.pop(fid)["path"]
                try:
                    os.remove(path)
                except OSError:
                    pass


def disp_param(header: str, key: str) -> str | None:
    match = re.search(rf'{key}="([^"]*)"', header)
    if match:
        return match.group(1)
    match = re.search(rf"{key}=([^;]+)", header)
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
    files = []
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
        headers = {}
        for line in head.decode("utf-8", "replace").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        disposition = headers.get("content-disposition", "")
        name = disp_param(disposition, "name") or ""
        filename = disp_param(disposition, "filename")
        if filename is not None:
            files.append({"filename": filename, "mime": headers.get("content-type", ""), "data": data})
        elif name:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


class Handler(BaseHTTPRequestHandler):
    server_version = "SendToMacSite/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_bytes(self, code: int, body: bytes, content_type: str, cache: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400" if cache else "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_obj(self, code: int, payload) -> None:
        self.send_bytes(code, json.dumps(payload).encode(), "application/json; charset=utf-8")

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length < 0 or length > MAX_FILE + 1024 * 1024:
            raise ValueError("Too large")
        return self.rfile.read(length)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/ws":
            self.handle_ws()
            return
        if parsed.path == "/api/info":
            self.send_obj(200, {
                "app": "sendtomac",
                "base": share_base(self.headers.get("Host", ""), self.server.server_address[1]),
                "mode": transfer_mode(),
            })
            return
        if parsed.path.startswith("/api/file/"):
            self.handle_download(parsed)
            return
        if parsed.path == "/vendor/qrcode.js" and VENDOR.is_file():
            self.send_bytes(200, VENDOR.read_bytes(), "text/javascript; charset=utf-8")
            return
        if parsed.path == "/theme.css":
            self.send_bytes(200, (ROOT / "web" / "theme.css").read_bytes(), "text/css; charset=utf-8")
            return
        if parsed.path == "/theme.js":
            self.send_bytes(200, (ROOT / "web" / "theme.js").read_bytes(), "text/javascript; charset=utf-8")
            return
        if parsed.path.startswith("/api/staged/"):
            self.handle_staged(parsed.path.rsplit("/", 1)[-1])
            return
        if parsed.path in ICONS:
            path, content_type = ICONS[parsed.path]
            if path.is_file():
                self.send_bytes(200, path.read_bytes(), content_type)
                return
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path in {"/privacy", "/privacy/", "/privacy.html"}:
            self.send_bytes(200, PRIVACY.read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path in {"/", "/index.html"} and not query.get("r"):
            self.send_bytes(200, LANDING.read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path in {"/", "/index.html", "/share", "/share/", "/site.html"}:
            if not PAGE.is_file():
                self.send_obj(500, {"ok": False, "error": "Missing page"})
                return
            self.send_bytes(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            return
        self.send_obj(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/save":
            self.handle_save()
            return
        if path != "/api/upload":
            self.send_obj(404, {"ok": False, "error": "Not found"})
            return
        try:
            fields, files = parse_multipart(self.headers.get("Content-Type", ""), self.read_body())
            if not files:
                raise ValueError("No file")
            incoming = files[0]
            if len(incoming["data"]) > MAX_FILE:
                raise ValueError("File is over 500 MB")
            result = store_upload(
                fields.get("token", ""),
                incoming["filename"],
                incoming["mime"],
                incoming["data"],
            )
            self.send_obj(200, result)
        except PermissionError as exc:
            self.send_obj(403, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            self.send_obj(400, {"ok": False, "error": str(exc)})

    def handle_staged(self, token: str) -> None:
        from staging import take_staged

        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self.send_obj(403, {"ok": False, "error": "Mac only"})
            return
        meta = take_staged(token)
        if not meta:
            self.send_obj(404, {"ok": False, "error": "Missing file"})
            return
        path = Path(meta["path"])
        if not path.is_file():
            self.send_obj(404, {"ok": False, "error": "Missing file"})
            return
        data = path.read_bytes()
        quoted = urllib.parse.quote(meta["name"])
        self.send_response(200)
        self.send_header("Content-Type", meta.get("mime") or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f"inline; filename=\"{meta['name']}\"; filename*=UTF-8''{quoted}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def handle_save(self) -> None:
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self.send_obj(403, {"ok": False, "error": "Mac only"})
            return
        try:
            _fields, files = parse_multipart(self.headers.get("Content-Type", ""), self.read_body())
            if not files:
                raise ValueError("No file")
            incoming = files[0]
            if len(incoming["data"]) > MAX_FILE:
                raise ValueError("File is over 500 MB")
            name = save_download(incoming["filename"], incoming["data"])
            self.send_obj(200, {"ok": True, "name": name, "folder": "Downloads/SendToMac"})
        except ValueError as exc:
            self.send_obj(400, {"ok": False, "error": str(exc)})

    def handle_download(self, parsed) -> None:
        file_id = parsed.path.rsplit("/", 1)[-1]
        token = (urllib.parse.parse_qs(parsed.query).get("token") or [""])[0]
        meta = take_file(file_id, token)
        if not meta or not os.path.isfile(meta["path"]):
            self.send_obj(404, {"ok": False, "error": "File expired"})
            return
        data = Path(meta["path"]).read_bytes()
        quoted = urllib.parse.quote(meta["name"])
        self.send_response(200)
        self.send_header("Content-Type", meta["mime"])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f"attachment; filename=\"{meta['name']}\"; filename*=UTF-8''{quoted}")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
        try:
            os.remove(meta["path"])
        except OSError:
            pass
        with LOCK:
            FILES.pop(file_id, None)

    def handle_ws(self) -> None:
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_obj(400, {"ok": False, "error": "Not a websocket"})
            return
        self.wfile.write(
            (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {ws_accept(key)}\r\n"
                "\r\n"
            ).encode()
        )
        self.wfile.flush()
        peer = None
        room_id = ""
        try:
            while True:
                frame = read_frame(self.rfile)
                if frame is None:
                    break
                opcode, data = frame
                if opcode == 8:
                    break
                if opcode == 9:
                    write_frame(self.wfile, 10, data)
                    continue
                if opcode != 1:
                    continue
                msg = json.loads(data.decode())
                if msg.get("type") in {"create", "join"}:
                    peer, room_id = self.hello(msg, peer)
                    continue
                if not peer:
                    continue
                if msg.get("type") == "signal":
                    for other in other_peers(ROOMS[room_id], peer["id"]):
                        send_json(other, {"type": "signal", "data": msg.get("data")})
                elif msg.get("type") == "text":
                    text = str(msg.get("text") or "")[:MAX_TEXT]
                    if text:
                        for other in other_peers(ROOMS[room_id], peer["id"]):
                            send_json(other, {"type": "text", "text": text})
        except (ConnectionError, json.JSONDecodeError, ValueError, OSError, KeyError):
            pass
        finally:
            if peer and room_id:
                drop_peer(room_id, peer["id"])
            self.close_connection = True

    def hello(self, msg: dict, existing: dict | None) -> tuple[dict, str]:
        requested = str(msg.get("room") or "")
        if msg.get("type") == "join":
            with LOCK:
                room = ROOMS.get(requested)
            if not room:
                write_frame(self.wfile, 1, json.dumps({"type": "error", "error": "That code expired. Scan again."}).encode())
                return existing or new_peer(self.wfile), ""
        else:
            room = ensure_room(requested if re.fullmatch(r"[a-z0-9]{8}", requested) else None)
        peer = existing or new_peer(self.wfile)
        err = add_peer(room, peer)
        if err == "full":
            write_frame(self.wfile, 1, json.dumps({"type": "error", "error": "That code is already in use."}).encode())
            return peer, ""
        role = "offer" if len(room["peers"]) == 1 else "answer"
        send_json(peer, {
            "type": "ready",
            "room": room["id"],
            "you": peer["id"],
            "token": peer["token"],
            "mode": room["mode"],
            "role": role,
            "base": share_base(self.headers.get("Host", ""), self.server.server_address[1]),
            "waiting": len(room["peers"]) < 2,
        })
        if len(room["peers"]) == 2:
            for other in list(room["peers"].values()):
                try:
                    send_json(other, {"type": "peer"})
                except OSError:
                    pass
        return peer, room["id"]


def ping(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/info", timeout=0.4) as res:
            return b'"app": "sendtomac"' in res.read()
    except (OSError, urllib.error.URLError):
        return False


class Server(ThreadingHTTPServer):
    # HTTPServer.server_bind reverse-looks up 0.0.0.0 and can stall on mDNS.
    def server_bind(self) -> None:
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        self.server_name = "sendtomac"
        self.server_port = self.server_address[1]


def serve(port: int) -> Server:
    last = None
    for candidate in range(port, port + 12):
        try:
            return Server(("0.0.0.0", candidate), Handler)
        except OSError as exc:
            last = exc
    raise SystemExit(f"No free port near {port}: {last}")


SAVE_DIR = Path.home() / "Downloads" / "SendToMac"


def as_app() -> bool:
    return getattr(sys, "frozen", False) or "--app" in sys.argv


def save_download(filename: str, data: bytes) -> str:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(safe_name(filename))
    dest = SAVE_DIR / stem.name
    n = 2
    while dest.exists():
        dest = SAVE_DIR / f"{stem.stem}-{n}{stem.suffix}"
        n += 1
    dest.write_bytes(data)
    return dest.name


def open_url(base: str) -> None:
    webbrowser.open(base.rstrip("/") + "/")


def open_window(url: str | None = None, ready=None) -> None:
    import webview
    page = {"url": url} if url else {"html": "<html><body style='margin:0;background:#efece6'></body></html>"}
    webview.create_window(
        "SendToMac",
        width=420,
        height=680,
        min_size=(380, 560),
        resizable=True,
        background_color="#efece6",
        text_select=True,
        **page,
    )
    # GUI must start on the main thread before the server, or the Intel build never shows the window.
    webview.start(ready)


def main() -> None:
    if "--self-test" in sys.argv:
        run_self_test()
        return
    existing = PORT if ping(PORT) else None
    if as_app():
        if existing and "--no-open" not in sys.argv:
            from menu_app import signal_running
            signal_running()
            return
        from menu_app import run_menu_app

        def start_server():
            threading.Thread(target=purge, daemon=True).start()
            httpd = serve(PORT)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            return httpd, httpd.server_address[1]

        run_menu_app(start_server)
        return
    if existing and "--no-open" not in sys.argv:
        ip = lan_ip()
        base = f"http://{ip or '127.0.0.1'}:{existing}"
        open_url(base)
        print(f"Already running at {base}/")
        return
    threading.Thread(target=purge, daemon=True).start()
    httpd = serve(PORT)
    bound = httpd.server_address[1]
    ip = lan_ip()
    url = f"http://{ip}:{bound}" if ip else f"http://127.0.0.1:{bound}"
    print(f"SendToMac: {url}/share", flush=True)
    print("Leave this running. Scan the QR with the phone. Same Wi-Fi.", flush=True)
    if "--no-open" not in sys.argv:
        open_url(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def run_self_test() -> None:
    fields, files = parse_multipart(
        "multipart/form-data; boundary=bound",
        b'--bound\r\nContent-Disposition: form-data; name="token"\r\n\r\nabc\r\n--bound\r\n'
        b'Content-Disposition: form-data; name="file"; filename="n.txt"\r\nContent-Type: text/plain\r\n\r\nhi\r\n'
        b"--bound--\r\n",
    )
    assert fields["token"] == "abc"
    assert files[0]["data"] == b"hi"
    assert safe_name("../x") == "x"
    print("self-test ok")


if __name__ == "__main__":
    main()
