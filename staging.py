"""Local-only files dropped onto the Mac window."""

from __future__ import annotations

import secrets
import threading
from pathlib import Path

LOCK = threading.Lock()
STAGED: dict[str, dict] = {}


def stage_local(path: Path) -> str:
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError("Not a file")
    path = path.resolve()
    if not path.is_file():
        raise ValueError("Not a file")
    if path.stat().st_size > 500 * 1024 * 1024:
        raise ValueError("File is over 500 MB")
    token = secrets.token_urlsafe(18)
    with LOCK:
        STAGED[token] = {"path": str(path), "name": path.name, "mime": "application/octet-stream"}
    return token


def take_staged(token: str) -> dict | None:
    with LOCK:
        return STAGED.pop(token, None)
