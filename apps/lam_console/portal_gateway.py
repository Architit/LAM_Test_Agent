#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from apps.lam_console.core import LocalHubCore


HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>LAM Portal Gateway</title></head>
<body style="font-family: monospace; background:#111; color:#0f0;">
<h2>LAM Portal Gateway</h2>
<p>Use API:</p>
<ul>
  <li>GET /api/status</li>
  <li>GET /api/pane/AGENTS|QUEUE|MODELS|BRIDGE|GATES</li>
  <li>POST /api/command {"command":"bridge-status"}</li>
</ul>
</body></html>
"""


class GatewayHandler(BaseHTTPRequestHandler):
    hub: LocalHubCore

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status: int, body: str) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        p = urlparse(self.path).path
        if p == "/":
            self._html(HTTPStatus.OK, HTML)
            return
        if p == "/api/status":
            result = self.hub.bridge_status()
            self._json(HTTPStatus.OK, {"ok": result.ok, "payload": result.payload})
            return
        if p == "/api/devices":
            self._json(HTTPStatus.OK, {"ok": True, "devices": self.hub.list_devices()})
            return
        if p.startswith("/api/pane/"):
            pane = p.split("/")[-1].upper()
            lines = self.hub.pane_snapshot(pane)
            self._json(HTTPStatus.OK, {"ok": True, "pane": pane, "lines": lines})
            return
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        p = urlparse(self.path).path
        if p != "/api/command":
            if p == "/api/device/send":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_json"})
                    return
                device_id = str(payload.get("device_id", "")).strip()
                message = str(payload.get("message", "")).strip()
                result = self.hub.send_device(device_id, message)
                self._json(HTTPStatus.OK, {"ok": result.ok, "title": result.title, "payload": result.payload})
                return
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_json"})
            return
        cmd = str(payload.get("command", "")).strip()
        if not cmd:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_command"})
            return
        result = self.hub.execute(cmd)
        self._json(HTTPStatus.OK, {"ok": result.ok, "title": result.title, "payload": result.payload})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM portal gateway daemon for cross-OS interface translation.")
    parser.add_argument("--mode", choices=["auto", "http", "file"], default="auto")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval-sec", type=int, default=2)
    return parser


def run_file_gateway(hub: LocalHubCore, interval_sec: int) -> int:
    status_file = hub.bridge_root / "portal_status.json"
    commands_file = hub.bridge_root / "portal_commands.jsonl"
    results_file = hub.bridge_root / "portal_results.jsonl"

    while True:
        status = hub.bridge_status().payload
        status_file.write_text(json.dumps(status, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

        if commands_file.exists():
            lines = commands_file.read_text(encoding="utf-8", errors="replace").splitlines()
            commands_file.write_text("", encoding="utf-8")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cmd = str(payload.get("command", "")).strip()
                if not cmd:
                    continue
                result = hub.execute(cmd)
                with results_file.open("a", encoding="utf-8") as fh:
                    fh.write(
                        json.dumps(
                            {
                                "ts_utc": status.get("ts_utc", ""),
                                "command": cmd,
                                "ok": result.ok,
                                "title": result.title,
                                "payload": result.payload,
                            },
                            ensure_ascii=True,
                        )
                        + "\n"
                    )
        time.sleep(interval_sec)


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    hub = LocalHubCore(repo_root)
    GatewayHandler.hub = hub
    if args.mode == "file":
        print(json.dumps({"status": "ok", "gateway_mode": "file", "bridge_root": str(hub.bridge_root)}, ensure_ascii=True))
        return run_file_gateway(hub, args.interval_sec)

    if args.mode == "http":
        with ThreadingHTTPServer((args.host, args.port), GatewayHandler) as srv:
            print(json.dumps({"status": "ok", "gateway": f"http://{args.host}:{args.port}"}, ensure_ascii=True))
            srv.serve_forever()
        return 0

    # auto mode: prefer HTTP, fallback to file mode.
    try:
        with ThreadingHTTPServer((args.host, args.port), GatewayHandler) as srv:
            print(json.dumps({"status": "ok", "gateway": f"http://{args.host}:{args.port}", "mode": "http"}, ensure_ascii=True))
            srv.serve_forever()
        return 0
    except PermissionError:
        print(json.dumps({"status": "warn", "mode": "file_fallback", "reason": "http_bind_denied"}, ensure_ascii=True))
        return run_file_gateway(hub, args.interval_sec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
