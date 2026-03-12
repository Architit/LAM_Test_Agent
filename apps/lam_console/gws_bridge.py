#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class GWSBridge:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.repo_name = repo_root.name
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.local_dir = Path(os.getenv("LAM_GWS_LOCAL_DIR", str(repo_root / ".gateway" / "exchange" / "gws")))
        drive_root = os.getenv("LAM_GWS_DRIVE_ROOT", os.getenv("GATEWAY_GWORKSPACE_ROOT", "")).strip()
        self.drive_root = Path(drive_root) if drive_root else None
        self.drive_dir = (self.drive_root / "LAM_GATEWAY" / self.repo_name) if self.drive_root else None

        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.local_dir.mkdir(parents=True, exist_ok=True)

        self.requests_file = self.bridge_root / "gws_requests.jsonl"
        self.results_file = self.bridge_root / "gws_results.jsonl"
        self.events_file = self.bridge_root / "events.jsonl"
        self.state_file = self.hub_root / "gws_bridge_state.json"

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def health(self) -> dict[str, Any]:
        gws_bin = shutil.which("gws") or str(Path.home() / ".local" / "bin" / "gws")
        has_gws = Path(gws_bin).exists() if gws_bin.startswith("/") else bool(shutil.which("gws"))
        has_rsync = shutil.which("rsync") is not None
        drive_configured = self.drive_root is not None
        drive_exists = bool(self.drive_root and self.drive_root.exists())
        return {
            "ts_utc": utc_now(),
            "repo": self.repo_name,
            "local_dir": str(self.local_dir),
            "drive_root": str(self.drive_root) if self.drive_root else "",
            "drive_dir": str(self.drive_dir) if self.drive_dir else "",
            "gws_present": has_gws,
            "rsync_present": has_rsync,
            "drive_configured": drive_configured,
            "drive_root_exists": drive_exists,
            "overall_ok": bool(has_rsync and drive_configured and drive_exists),
        }

    @staticmethod
    def _run(cmd: list[str], timeout_sec: int = 120) -> tuple[int, str, str]:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_sec, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    def _sync(self, pull: bool) -> dict[str, Any]:
        if not self.drive_dir:
            return {"ok": False, "error": "drive_root_not_configured"}
        self.drive_dir.mkdir(parents=True, exist_ok=True)
        src = str(self.drive_dir) + "/" if pull else str(self.local_dir) + "/"
        dst = str(self.local_dir) + "/" if pull else str(self.drive_dir) + "/"
        rc, out, err = self._run(["rsync", "-a", "--delete", src, dst], timeout_sec=180)
        return {"ok": rc == 0, "rc": rc, "stdout": out, "stderr": err, "direction": "pull" if pull else "push"}

    def _put(self, src: str, target_rel: str = "") -> dict[str, Any]:
        path = Path(src)
        if not path.exists() or not path.is_file():
            return {"ok": False, "error": f"source_missing: {src}"}
        target = self.local_dir / (target_rel or path.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        return {"ok": True, "stored": str(target)}

    def _get(self, source_rel: str, dst: str) -> dict[str, Any]:
        source = self.local_dir / source_rel
        if not source.exists() or not source.is_file():
            return {"ok": False, "error": f"source_missing: {source_rel}"}
        dst_path = Path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dst_path)
        return {"ok": True, "output": str(dst_path)}

    def _list(self, prefix: str = "", limit: int = 100) -> dict[str, Any]:
        base = self.local_dir / prefix
        if not base.exists():
            return {"ok": False, "error": f"path_missing: {prefix}"}
        files: list[str] = []
        if base.is_file():
            files.append(str(base.relative_to(self.local_dir)))
        else:
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    files.append(str(p.relative_to(self.local_dir)))
                if len(files) >= limit:
                    break
        return {"ok": True, "files": files, "count": len(files)}

    def handle(self, req: dict[str, Any]) -> dict[str, Any]:
        op = str(req.get("op", "")).strip().lower()
        if op == "health":
            payload = self.health()
            return {"ok": True, "result": payload}
        if op == "sync_push":
            return self._sync(pull=False)
        if op == "sync_pull":
            return self._sync(pull=True)
        if op == "put":
            return self._put(str(req.get("src", "")), str(req.get("target_rel", "")))
        if op == "get":
            return self._get(str(req.get("source_rel", "")), str(req.get("dst", "")))
        if op == "list":
            return self._list(str(req.get("prefix", "")), int(req.get("limit", 100)))
        return {"ok": False, "error": f"unknown_op: {op}"}

    def run_once(self) -> dict[str, Any]:
        processed = 0
        requests: list[dict[str, Any]] = []
        if self.requests_file.exists():
            raw = self.requests_file.read_text(encoding="utf-8", errors="replace").splitlines()
            self.requests_file.write_text("", encoding="utf-8")
            for line in raw:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    requests.append(obj)

        for req in requests:
            req_id = str(req.get("id", f"gws_{int(time.time()*1000)}"))
            res = self.handle(req)
            envelope = {"id": req_id, "ts_utc": utc_now(), "request": req, "response": res}
            self._append_jsonl(self.results_file, envelope)
            self._append_jsonl(self.events_file, {"ts_utc": utc_now(), "event": "gws_bridge_request", "id": req_id, "ok": bool(res.get("ok"))})
            processed += 1

        state = {"ts_utc": utc_now(), "processed": processed, "health": self.health()}
        self.state_file.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return state



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM local GWS bridge (queue-based).")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--interval-sec", type=int, default=5, help="Daemon poll interval.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    bridge = GWSBridge(repo_root)

    if args.once:
        print(json.dumps(bridge.run_once(), ensure_ascii=True))
        return 0

    while True:
        payload = bridge.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "processed": payload.get("processed")}, ensure_ascii=True))
        time.sleep(max(1, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
