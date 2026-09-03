#!/usr/bin/env python3
"""
MakeSlide - Live Slide Editor local server (stdlib only)

Serves a directory that contains an index.html presentation and provides a
POST /api/save endpoint so the in-browser Live Slide Editor (press E) can
persist edits back to index.html on disk. Keeps the "no dependencies"
philosophy of make-slide: only the Python standard library is used.

Usage:
    python3 scripts/live_editor_server.py [directory]
    python3 scripts/live_editor_server.py [directory] --port 8080
    python3 scripts/live_editor_server.py [directory] --no-browser

Defaults:
    directory  -> current working directory
    port       -> first free port from 5678 (scan up to +49)
    browser    -> opens automatically unless --no-browser
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_PORT = 5678
PORT_SPAN = 50
SAVE_FILENAME = "crypto-strategy-lab-slides.html"
ANNOTATIONS_FILENAME = "annotations.jsonl"


def validate_port(port: int) -> int:
    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError("port must be an integer between 1 and 65535")
    if not 1 <= port <= 65535:
        raise ValueError(f"port must be between 1 and 65535: {port}")
    return port


def find_free_port(preferred: int, host: str = "127.0.0.1", span: int = 50) -> int:
    """Return the first bindable port starting from ``preferred``."""
    preferred = validate_port(preferred)
    if span <= 0:
        raise ValueError("span must be positive")
    last = min(preferred + span - 1, 65535)
    for port in range(preferred, last + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"no free TCP port on {host} in range {preferred}..{last}"
    )


class SaveHandler(SimpleHTTPRequestHandler):
    """Serve the directory and handle /api/save + /api/health."""

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True})
            return
        if path == "/api/save":
            self._handle_save()
            return
        if path == "/api/annotations":
            self._handle_annotations_post()
            return
        self._send_json({"ok": False, "error": f"unknown path: {path}"}, 404)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True})
            return
        if path == "/api/annotations":
            self._send_json({"ok": True, "annotations": self._read_annotations()})
            return
        super().do_GET()

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/annotations":
            self._clear_annotations()
            self._send_json({"ok": True, "cleared": True})
            return
        self._send_json({"ok": False, "error": f"unknown path: {path}"}, 404)

    # --- index.html save ---------------------------------------------------
    def _handle_save(self) -> None:
        body = self._body()
        if not body.strip():
            self._send_json({"ok": False, "error": "empty body"}, 400)
            return
        # Write raw bytes verbatim so OS newline translation never corrupts the
        # document (browsers send \n; text-mode writes could double it on Windows).
        target = Path(self.directory) / SAVE_FILENAME
        try:
            target.write_bytes(body)
        except OSError as exc:
            self._send_json({"ok": False, "error": str(exc)}, 500)
            return
        self._send_json({"ok": True, "saved": target.name, "bytes": len(body)})

    # --- annotations -------------------------------------------------------
    @property
    def _annotations_file(self) -> Path:
        return Path(self.directory) / ANNOTATIONS_FILENAME

    def _read_annotations(self) -> list[dict]:
        f = self._annotations_file
        if not f.exists():
            return []
        out: list[dict] = []
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
        return out

    def _append_annotations(self, records: list) -> None:
        f = self._annotations_file
        with f.open("a", encoding="utf-8", newline="\n") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _clear_annotations(self) -> None:
        self._annotations_file.unlink(missing_ok=True)

    def _handle_annotations_post(self) -> None:
        raw = self._body()
        if not raw.strip():
            self._send_json({"ok": False, "error": "empty body"}, 400)
            return
        try:
            records = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json({"ok": False, "error": "invalid JSON"}, 400)
            return
        if not isinstance(records, list):
            self._send_json({"ok": False, "error": "expected a JSON array"}, 400)
            return
        for rec in records:
            if isinstance(rec, dict):
                rec["ts"] = int(time.time())
        self._append_annotations(records)
        self._send_json({"ok": True, "count": len(records)})

    def log_message(self, fmt: str, *args) -> None:
        # Quiet: only surface save actions for clarity. Some http.server
        # 404/error paths pass an HTTPStatus enum (not str) as args[0]; skip
        # those so log_message never raises.
        msg = args[0] if args else ""
        if not isinstance(msg, str):
            return
        if any(k in msg for k in ("/api/save", "/api/health", "/api/annotations", SAVE_FILENAME)):
            sys.stderr.write(f"[make-slide editor] {msg}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="MakeSlide Live Slave Editor server")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Directory containing index.html (default: cwd)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Preferred port (default {DEFAULT_PORT}, scans up to +49)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open a browser automatically")
    args = parser.parse_args()

    serve_dir = Path(args.directory).resolve()
    if not serve_dir.is_dir():
        print(f"error: not a directory: {serve_dir}", file=sys.stderr)
        return 1

    index_path = serve_dir / SAVE_FILENAME
    if not index_path.exists():
        print(f"warning: {index_path} not found; editor save will create it", file=sys.stderr)

    try:
        port = find_free_port(args.port)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    handler = lambda *a, **k: SaveHandler(*a, directory=str(serve_dir), **k)  # type: ignore[misc]
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True

    url = f"http://127.0.0.1:{port}/{SAVE_FILENAME}"
    print(f"[make-slide editor] serving {serve_dir}")
    print(f"[make-slide editor] Press E in the browser to edit; Save writes back to {index_path}")
    print(f"[make-slide editor] URL: {url}")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[make-slide editor] stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
