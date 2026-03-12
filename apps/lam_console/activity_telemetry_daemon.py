#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_stat_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def summarize_tree(root: Path, max_depth: int = 6) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "files": 0, "bytes": 0}
    files = 0
    total = 0
    base_depth = len(root.parts)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if len(p.parts) - base_depth > max_depth:
            continue
        files += 1
        try:
            total += int(p.stat().st_size)
        except OSError:
            continue
    return {"exists": True, "files": files, "bytes": total}


def tail_lines(path: Path, limit: int = 2000) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def count_recent_jsonl(path: Path, since_epoch: float) -> int:
    rows = tail_lines(path, 4000)
    count = 0
    for line in rows:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = str(payload.get("ts_utc", "")).strip()
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.timestamp() >= since_epoch:
            count += 1
    return count


def find_db_files(repo_root: Path, limit: int = 80) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            continue
        try:
            size = int(p.stat().st_size)
        except OSError:
            size = 0
        out.append({"path": str(p), "bytes": size})
        if len(out) >= limit:
            break
    return out


class ActivityTelemetry:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.state_file = self.hub_root / "activity_telemetry_state.json"
        self.timeline_file = self.hub_root / "activity_telemetry_timeline.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"

        self.bridge_events = self.bridge_root / "events.jsonl"
        self.bridge_commands = self.bridge_root / "commands.jsonl"
        self.routing_events = repo_root / ".gateway" / "routing_events.jsonl"
        self.runtime_log = repo_root / "memory" / "FRONT" / "LAM_RUNTIME_LOG.jsonl"
        self.bg_errors = repo_root / ".gateway" / "test_runs" / "background" / "errors.jsonl"

        self.archive_roots = {
            "memory_archive": repo_root / "memory" / "ARCHIVE",
            "archive_shadows": repo_root / "data" / "local" / "ARCHIVE_SHADOWS",
            "chronolog": repo_root / "chronolog",
            "journal": repo_root / "journal",
        }

    def collect(self) -> dict[str, Any]:
        now = time.time()
        last_5m = now - 300
        last_60m = now - 3600

        activity = {
            "bridge_events_5m": count_recent_jsonl(self.bridge_events, last_5m),
            "bridge_commands_5m": count_recent_jsonl(self.bridge_commands, last_5m),
            "routing_events_60m": count_recent_jsonl(self.routing_events, last_60m),
            "runtime_events_60m": count_recent_jsonl(self.runtime_log, last_60m),
            "background_errors_60m": count_recent_jsonl(self.bg_errors, last_60m),
        }

        archives = {name: summarize_tree(path) for name, path in self.archive_roots.items()}
        db_files = find_db_files(self.repo_root)
        db_total = sum(int(x.get("bytes", 0)) for x in db_files)

        signals = {
            "activity_score": int(activity["bridge_events_5m"] + activity["bridge_commands_5m"] + activity["routing_events_60m"] / 2),
            "archive_bytes_total": sum(int(x.get("bytes", 0)) for x in archives.values()),
            "db_files_total": len(db_files),
            "db_bytes_total": db_total,
            "bridge_events_staleness_sec": int(max(0, now - safe_stat_mtime(self.bridge_events))),
            "runtime_log_staleness_sec": int(max(0, now - safe_stat_mtime(self.runtime_log))),
        }

        return {
            "ts_utc": utc_now(),
            "activity": activity,
            "archives": archives,
            "databases": {"count": len(db_files), "bytes_total": db_total, "files": db_files[:20]},
            "signals": signals,
        }

    def run_once(self) -> dict[str, Any]:
        payload = self.collect()
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        with self.timeline_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
        with self.audit_stream_file.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"ts_utc": payload["ts_utc"], "source": "activity_telemetry", "event": "activity_snapshot", "payload": payload},
                    ensure_ascii=True,
                )
                + "\n"
            )
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Activity telemetry daemon (archives + db + runtime signals).")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=20)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = ActivityTelemetry(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = svc.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "score": payload.get("signals", {}).get("activity_score", 0)}, ensure_ascii=True))
        time.sleep(max(5, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
