#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts_utc(raw: str) -> float | None:
    val = str(raw or "").strip()
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def tail_jsonl(path: Path, limit: int = 8000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    out: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def classify_domain(event: dict[str, Any]) -> str:
    s = json.dumps(event, ensure_ascii=True).lower()
    if any(x in s for x in ("keyboard", "key_", "keypress", "keycode")):
        return "keyboard"
    if any(x in s for x in ("mouse", "pointer", "scroll", "hover")):
        return "pointer"
    if any(x in s for x in ("touch", "button", "click", "press")):
        return "buttons_touch"
    if any(x in s for x in ("sensor", "telemetry", "temperature", "gyro", "accel")):
        return "sensors"
    if any(x in s for x in ("scanner", "scan")):
        return "scanners"
    if any(x in s for x in ("kernel", "core", "module", "component", "driver")):
        return "core_modules"
    if any(x in s for x in ("zone", "pane", "surface", "environment", "space")):
        return "zones_spaces"
    if any(x in s for x in ("inbox", "ingress", "receive")):
        return "io_in"
    if any(x in s for x in ("outbox", "egress", "dispatch", "send")):
        return "io_out"
    return "generic"


def extract_ms_values(obj: Any, out: list[float], depth: int = 0) -> None:
    if depth > 5:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            if isinstance(v, (int, float)) and key.endswith("_ms"):
                out.append(float(v))
            else:
                extract_ms_values(v, out, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:64]:
            extract_ms_values(item, out, depth + 1)


def compute_freq_bands(freq_hz: list[float]) -> dict[str, int]:
    bands = {
        "ultra_low_0_0_5hz": 0,
        "low_0_5_2hz": 0,
        "mid_2_8hz": 0,
        "high_8_32hz": 0,
        "ultra_high_32hz_plus": 0,
    }
    for f in freq_hz:
        if f < 0.5:
            bands["ultra_low_0_0_5hz"] += 1
        elif f < 2:
            bands["low_0_5_2hz"] += 1
        elif f < 8:
            bands["mid_2_8hz"] += 1
        elif f < 32:
            bands["high_8_32hz"] += 1
        else:
            bands["ultra_high_32hz_plus"] += 1
    return bands


def compute_io_vector(freq_bands: dict[str, int]) -> dict[str, float]:
    keys = [
        "ultra_low_0_0_5hz",
        "low_0_5_2hz",
        "mid_2_8hz",
        "high_8_32hz",
        "ultra_high_32hz_plus",
    ]
    total = float(sum(int(freq_bands.get(k, 0)) for k in keys))
    if total <= 0:
        return {k: 0.0 for k in keys}
    return {k: round(float(freq_bands.get(k, 0)) / total, 4) for k in keys}


class IOSpectralAnalyzer:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.state_file = self.hub_root / "io_spectral_state.json"
        self.timeline_file = self.hub_root / "io_spectral_timeline.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"

        self.bridge_events = self.bridge_root / "events.jsonl"
        self.bridge_commands = self.bridge_root / "commands.jsonl"

    def collect(self) -> dict[str, Any]:
        now = time.time()
        window_sec = int(os.getenv("LAM_IO_SPECTRAL_WINDOW_SEC", "600"))
        since = now - window_sec

        rows = tail_jsonl(self.bridge_events, limit=12000) + tail_jsonl(self.bridge_commands, limit=12000)
        rows.sort(key=lambda x: str(x.get("ts_utc", "")))

        ts_rows: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            ts = parse_ts_utc(str(row.get("ts_utc", "")))
            if ts is None or ts < since:
                continue
            ts_rows.append((ts, row))

        domain_counts: dict[str, int] = {}
        domain_ts: dict[str, list[float]] = {}
        ms_values: list[float] = []
        for ts, row in ts_rows:
            domain = classify_domain(row)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            domain_ts.setdefault(domain, []).append(ts)
            extract_ms_values(row, ms_values)

        freq_samples: list[float] = []
        for values in domain_ts.values():
            if len(values) < 2:
                continue
            for i in range(1, len(values)):
                dt = values[i] - values[i - 1]
                if dt <= 0.001:
                    continue
                freq_samples.append(1.0 / dt)

        freq_bands = compute_freq_bands(freq_samples)
        io_vector = compute_io_vector(freq_bands)

        latency = {
            "sample_count": len(ms_values),
            "p50_ms": round(statistics.median(ms_values), 3) if ms_values else 0.0,
            "p95_ms": round(statistics.quantiles(ms_values, n=20)[18], 3) if len(ms_values) >= 20 else (round(max(ms_values), 3) if ms_values else 0.0),
            "max_ms": round(max(ms_values), 3) if ms_values else 0.0,
        }
        top_domain = ""
        if domain_counts:
            top_domain = max(domain_counts.items(), key=lambda kv: kv[1])[0]

        rates_hz = {k: round(v / max(1.0, float(window_sec)), 4) for k, v in domain_counts.items()}
        signals = {
            "spectral_pressure": round(
                io_vector.get("high_8_32hz", 0.0) + (io_vector.get("ultra_high_32hz_plus", 0.0) * 1.5),
                4,
            ),
            "dominant_domain": top_domain,
            "io_event_count_window": len(ts_rows),
            "window_sec": window_sec,
        }
        return {
            "ts_utc": utc_now(),
            "window_sec": window_sec,
            "counts": domain_counts,
            "rates_hz": rates_hz,
            "frequency_bands": freq_bands,
            "io_vector": io_vector,
            "latency": latency,
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
                    {"ts_utc": payload["ts_utc"], "source": "io_spectral", "event": "io_spectral_snapshot", "payload": payload},
                    ensure_ascii=True,
                )
                + "\n"
            )
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vector spectral analysis of IO/input-response telemetry.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=12)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = IOSpectralAnalyzer(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = svc.run_once()
        print(
            json.dumps(
                {
                    "ts_utc": payload.get("ts_utc"),
                    "dominant_domain": payload.get("signals", {}).get("dominant_domain", ""),
                    "spectral_pressure": payload.get("signals", {}).get("spectral_pressure", 0.0),
                },
                ensure_ascii=True,
            )
        )
        time.sleep(max(3, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
