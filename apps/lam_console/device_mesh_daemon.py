#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_mesh_module(repo_root: Path):
    script = repo_root / "scripts" / "device_meshctl.py"
    spec = importlib.util.spec_from_file_location("device_meshctl", script)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load mesh module: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Realtime device mesh daemon.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=15)
    parser.add_argument("--direction", default="bidirectional")
    return parser


def run_once(repo_root: Path, direction: str) -> dict:
    module = load_mesh_module(repo_root)
    ctl = module.DeviceMeshCtl(repo_root)
    result = ctl.sync_once("all", direction)

    hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
    bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
    state_file = hub_root / "device_mesh_state.json"
    events_file = bridge_root / "events.jsonl"
    state = {"ts_utc": utc_now(), "direction": direction, **result}
    hub_root.mkdir(parents=True, exist_ok=True)
    bridge_root.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    with events_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts_utc": utc_now(), "event": "device_mesh_daemon_cycle", "state": state}, ensure_ascii=True) + "\n")
    return state


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    if args.once:
        print(json.dumps(run_once(repo_root, args.direction), ensure_ascii=True))
        return 0
    while True:
        state = run_once(repo_root, args.direction)
        print(json.dumps({"ts_utc": state.get("ts_utc"), "dispatched": state.get("dispatched", 0)}, ensure_ascii=True))
        time.sleep(max(3, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
