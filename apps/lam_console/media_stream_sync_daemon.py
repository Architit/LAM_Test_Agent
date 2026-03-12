#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return ""


def scan_tree(root: Path, max_files: int = 5000) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return out
    count = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = safe_rel(p, root)
        if not rel:
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        out[rel] = {
            "size": int(st.st_size),
            "mtime_ns": int(st.st_mtime_ns),
        }
        count += 1
        if count >= max_files:
            break
    return out


def choose_copy_direction(src: dict[str, Any] | None, dst: dict[str, Any] | None, mode: str) -> str:
    if mode == "push":
        return "src_to_dst" if src is not None else "none"
    if mode == "pull":
        return "dst_to_src" if dst is not None else "none"
    # bidirectional
    if src is None and dst is None:
        return "none"
    if src is None:
        return "dst_to_src"
    if dst is None:
        return "src_to_dst"
    if int(src.get("mtime_ns", 0)) > int(dst.get("mtime_ns", 0)):
        return "src_to_dst"
    if int(dst.get("mtime_ns", 0)) > int(src.get("mtime_ns", 0)):
        return "dst_to_src"
    if int(src.get("size", 0)) != int(dst.get("size", 0)):
        return "src_to_dst"
    return "none"


def lock_name(rel_path: str) -> str:
    return rel_path.replace("/", "__").replace("\\", "__")


def classify_sync_class(rel: str) -> str:
    p = rel.strip().lower()
    if p.startswith("protocols/") or "/protocols/" in p or "/protocol/" in p:
        return "protocols"
    if p.startswith("instructions/") or "/instructions/" in p:
        return "instructions"
    if p.startswith("contracts/") or "/contracts/" in p or "/contract/" in p:
        return "contracts"
    if p.startswith("policies/") or "/policies/" in p or "/policy/" in p:
        return "policies"
    if p.startswith("licenses/") or "/licenses/" in p or "/license/" in p:
        return "licenses"
    if p.startswith("map/") or "/map/" in p or "/maps/" in p:
        return "map"
    if p.startswith("cards/") or "/cards/" in p or "/card/" in p:
        return "cards"
    if "key pass" in p or "keypass" in p or "passcode" in p or "dna" in p or "dnagen" in p:
        return "keypass_code_dnagen"
    return "other"


def parse_class_order(raw: str) -> list[str]:
    values = [x.strip().lower() for x in raw.split(",") if x.strip()]
    out: list[str] = []
    for v in values:
        if v not in out:
            out.append(v)
    for v in ("instructions", "contracts", "protocols", "policies", "licenses", "map", "cards", "keypass_code_dnagen", "other"):
        if v not in out:
            out.append(v)
    return out


def parse_class_max_ops(raw: str) -> dict[str, int]:
    out = {
        "instructions": 16,
        "contracts": 12,
        "protocols": 10,
        "policies": 8,
        "licenses": 8,
        "map": 6,
        "cards": 6,
        "keypass_code_dnagen": 4,
        "other": 4,
    }
    for chunk in [x.strip() for x in raw.split(",") if x.strip()]:
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        k = key.strip().lower()
        if k not in out:
            continue
        try:
            n = int(value.strip())
        except ValueError:
            continue
        out[k] = max(0, n)
    return out


class MediaStreamSync:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.device_root = Path(os.getenv("LAM_MEDIA_DEVICE_ROOT", str(repo_root / ".gateway" / "exchange" / "device")))
        self.removable_root = Path(os.getenv("LAM_MEDIA_REMOVABLE_ROOT", str(repo_root / ".gateway" / "exchange" / "removable")))
        self.device_root.mkdir(parents=True, exist_ok=True)
        self.removable_root.mkdir(parents=True, exist_ok=True)

        self.state_file = self.hub_root / "media_stream_sync_state.json"
        self.timeline_file = self.hub_root / "media_stream_sync_timeline.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.events_file = self.bridge_root / "events.jsonl"

        self.zone_root = Path(os.getenv("LAM_MEDIA_SYNC_ZONE_ROOT", str(repo_root / ".gateway" / "sync_zones" / "media_sync")))
        self.active_locks = self.zone_root / "active"
        self.logs_dir = self.zone_root / "ticks"
        self.locks_file = self.zone_root / "locks.tsv"
        self.zones_file = self.zone_root / "zones.tsv"
        self.active_locks.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if not self.locks_file.exists():
            self.locks_file.write_text("tick\tscope\tstatus\tts_utc\n", encoding="utf-8")
        if not self.zones_file.exists():
            self.zones_file.write_text("tick\tzone\tphase\tscope\tstatus\tstart_utc\tend_utc\tlog\n", encoding="utf-8")

        self.mode = os.getenv("LAM_MEDIA_SYNC_MODE", "bidirectional").strip().lower()
        self.max_ops = int(os.getenv("LAM_MEDIA_SYNC_MAX_OPS_PER_TICK", "32"))
        self.max_scan_files = int(os.getenv("LAM_MEDIA_SYNC_MAX_SCAN_FILES", "8000"))
        self.class_order = parse_class_order(
            os.getenv(
                "LAM_MEDIA_SYNC_CLASS_ORDER",
                "instructions,contracts,protocols,policies,licenses,map,cards,keypass_code_dnagen,other",
            )
        )
        self.class_max_ops = parse_class_max_ops(
            os.getenv(
                "LAM_MEDIA_SYNC_CLASS_MAX_OPS",
                "instructions:16,contracts:12,protocols:10,policies:8,licenses:8,map:6,cards:6,keypass_code_dnagen:4,other:4",
            )
        )
        self.tick_counter = 0

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _mark_lock(self, tick: int, scope: str, status: str) -> None:
        ts = utc_now()
        with self.locks_file.open("a", encoding="utf-8") as fh:
            fh.write(f"{tick}\t{scope}\t{status}\t{ts}\n")

    def _try_lock(self, rel: str) -> Path | None:
        lk = self.active_locks / f"{lock_name(rel)}.lock"
        try:
            fd = os.open(str(lk), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.write(fd, f"{utc_now()} {rel}\n".encode("utf-8"))
            os.close(fd)
            return lk
        except FileExistsError:
            return None

    def _unlock(self, lk: Path) -> None:
        try:
            lk.unlink(missing_ok=True)
        except OSError:
            return

    def _copy(self, src_root: Path, dst_root: Path, rel: str) -> tuple[bool, str]:
        src = src_root / rel
        dst = dst_root / rel
        if not src.exists():
            return False, "src_missing"
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
            return True, "ok"
        except OSError as exc:
            return False, str(exc)

    def run_once(self) -> dict[str, Any]:
        self.tick_counter += 1
        tick = self.tick_counter
        start_utc = utc_now()
        tick_log = self.logs_dir / f"tick_{tick:06d}.log"

        src_scan = scan_tree(self.device_root, max_files=self.max_scan_files)
        dst_scan = scan_tree(self.removable_root, max_files=self.max_scan_files)
        all_rel = sorted(set(src_scan.keys()) | set(dst_scan.keys()))
        class_candidates: dict[str, list[tuple[str, str]]] = {k: [] for k in self.class_order}
        planned_by_class: dict[str, int] = {k: 0 for k in self.class_order}
        applied_by_class: dict[str, int] = {k: 0 for k in self.class_order}
        skipped_locked_by_class: dict[str, int] = {k: 0 for k in self.class_order}
        conflicts_by_class: dict[str, int] = {k: 0 for k in self.class_order}
        for rel in all_rel:
            direction = choose_copy_direction(src_scan.get(rel), dst_scan.get(rel), self.mode)
            if direction == "none":
                continue
            cls = classify_sync_class(rel)
            if cls not in class_candidates:
                class_candidates[cls] = []
                planned_by_class[cls] = 0
                applied_by_class[cls] = 0
                skipped_locked_by_class[cls] = 0
                conflicts_by_class[cls] = 0
            class_candidates[cls].append((rel, direction))

        applied = 0
        skipped_locked = 0
        conflicts = 0
        planned = 0
        logs: list[str] = []
        for cls in self.class_order:
            cls_budget = int(self.class_max_ops.get(cls, 0))
            if cls_budget <= 0:
                continue
            cls_used = 0
            for rel, direction in class_candidates.get(cls, []):
                if planned >= self.max_ops or cls_used >= cls_budget:
                    break
                planned += 1
                planned_by_class[cls] = int(planned_by_class.get(cls, 0)) + 1
                cls_used += 1
                scope = rel
                self._mark_lock(tick, scope, "active")
                lk = self._try_lock(rel)
                if lk is None:
                    skipped_locked += 1
                    skipped_locked_by_class[cls] = int(skipped_locked_by_class.get(cls, 0)) + 1
                    self._mark_lock(tick, scope, "released")
                    logs.append(f"skip_locked {cls} {rel}")
                    continue
                try:
                    if direction == "src_to_dst":
                        ok, msg = self._copy(self.device_root, self.removable_root, rel)
                    else:
                        ok, msg = self._copy(self.removable_root, self.device_root, rel)
                    if ok:
                        applied += 1
                        applied_by_class[cls] = int(applied_by_class.get(cls, 0)) + 1
                        logs.append(f"applied {cls} {direction} {rel}")
                    else:
                        conflicts += 1
                        conflicts_by_class[cls] = int(conflicts_by_class.get(cls, 0)) + 1
                        logs.append(f"conflict {cls} {direction} {rel} {msg}")
                finally:
                    self._unlock(lk)
                    self._mark_lock(tick, scope, "released")
            if planned >= self.max_ops:
                break

        tick_log.write_text("\n".join(logs) + ("\n" if logs else ""), encoding="utf-8")
        end_utc = utc_now()
        with self.zones_file.open("a", encoding="utf-8") as fh:
            fh.write(f"{tick}\t{self.zone_root}\tmedia_sync\tdevice,removable\tok\t{start_utc}\t{end_utc}\t{tick_log}\n")

        payload = {
            "ts_utc": end_utc,
            "tick": tick,
            "mode": self.mode,
            "device_root": str(self.device_root),
            "removable_root": str(self.removable_root),
            "planned_ops": planned,
            "applied_ops": applied,
            "skipped_locked_ops": skipped_locked,
            "conflict_ops": conflicts,
            "planned_by_class": planned_by_class,
            "applied_by_class": applied_by_class,
            "skipped_locked_by_class": skipped_locked_by_class,
            "conflicts_by_class": conflicts_by_class,
            "class_order": self.class_order,
            "class_max_ops": self.class_max_ops,
            "max_ops_per_tick": self.max_ops,
            "max_scan_files": self.max_scan_files,
            "locks_file": str(self.locks_file),
            "zones_file": str(self.zones_file),
            "tick_log": str(tick_log),
            "signals": {
                "sync_pressure": round(float(planned) / max(1, self.max_ops), 4),
                "lock_pressure": round(float(skipped_locked) / max(1, planned), 4) if planned > 0 else 0.0,
                "status": "ok" if conflicts == 0 else "degraded",
            },
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._append_jsonl(self.timeline_file, payload)
        self._append_jsonl(
            self.events_file,
            {"ts_utc": payload["ts_utc"], "event": "media_stream_sync_tick", "planned": planned, "applied": applied, "conflicts": conflicts},
        )
        self._append_jsonl(
            self.audit_stream_file,
            {"ts_utc": payload["ts_utc"], "source": "media_stream_sync", "event": "snapshot", "payload": payload},
        )
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Realtime stream sync between device storage and removable media with microtick isolation.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=6)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = MediaStreamSync(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = svc.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "applied": payload.get("applied_ops", 0), "status": payload.get("signals", {}).get("status", "ok")}, ensure_ascii=True))
        time.sleep(max(2, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
