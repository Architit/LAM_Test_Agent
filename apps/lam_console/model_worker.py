#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_now() -> int:
    return int(time.time())


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


class ModelDeliveryWorker:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.spool_dir = self.hub_root / "model_spool"
        self.outbox_dir = self.hub_root / "outbox"
        self.dead_letter_file = self.hub_root / "dead_letter.jsonl"
        self.state_file = self.hub_root / "worker_state.json"
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.bridge_events = self.bridge_root / "events.jsonl"

        self.max_attempts = int(os.getenv("LAM_MODEL_WORKER_MAX_ATTEMPTS", "5"))
        self.backoff_base_sec = int(os.getenv("LAM_MODEL_WORKER_BACKOFF_BASE_SEC", "5"))
        self.backoff_cap_sec = int(os.getenv("LAM_MODEL_WORKER_BACKOFF_CAP_SEC", "300"))
        self.breaker_threshold = int(os.getenv("LAM_MODEL_WORKER_BREAKER_THRESHOLD", "3"))
        self.breaker_cooldown_sec = int(os.getenv("LAM_MODEL_WORKER_BREAKER_COOLDOWN_SEC", "120"))
        self.timeout_sec = int(os.getenv("LAM_MODEL_WORKER_TIMEOUT_SEC", "30"))

        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.endpoints = {
            "codex": os.getenv("LAM_CODEX_ENDPOINT", "").strip(),
            "gemini": os.getenv("LAM_GEMINI_ENDPOINT", "").strip(),
        }

    def load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {"attempts": {}, "breakers": {}, "last_run_utc": ""}
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def save_state(self, state: dict[str, Any]) -> None:
        state["last_run_utc"] = utc_now()
        self.state_file.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def _send(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        if raw.startswith("{") and raw.endswith("}"):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return {"raw": raw}

    def _breaker_open(self, state: dict[str, Any], provider: str) -> bool:
        breaker = state.setdefault("breakers", {}).setdefault(provider, {"failures": 0, "open_until_epoch": 0})
        return int(breaker.get("open_until_epoch", 0)) > epoch_now()

    def _breaker_fail(self, state: dict[str, Any], provider: str) -> None:
        breaker = state.setdefault("breakers", {}).setdefault(provider, {"failures": 0, "open_until_epoch": 0})
        breaker["failures"] = int(breaker.get("failures", 0)) + 1
        if int(breaker["failures"]) >= self.breaker_threshold:
            breaker["open_until_epoch"] = epoch_now() + self.breaker_cooldown_sec

    def _breaker_ok(self, state: dict[str, Any], provider: str) -> None:
        state.setdefault("breakers", {})[provider] = {"failures": 0, "open_until_epoch": 0}

    def _attempt_key(self, rec: dict[str, Any]) -> str:
        rid = str(rec.get("id", "")).strip()
        if rid:
            return rid
        return f"{rec.get('provider','')}::{hash(json.dumps(rec, ensure_ascii=True, sort_keys=True))}"

    def _next_backoff(self, attempt: int) -> int:
        return min(self.backoff_cap_sec, self.backoff_base_sec * (2 ** max(0, attempt - 1)))

    def run_once(self) -> dict[str, Any]:
        state = self.load_state()
        attempts = state.setdefault("attempts", {})
        totals = {"processed": 0, "sent": 0, "failed": 0, "dead": 0, "skipped": 0}

        for spool_file in sorted(self.spool_dir.glob("*.jsonl")):
            provider = spool_file.stem.lower()
            endpoint = self.endpoints.get(provider, "")
            unresolved: list[dict[str, Any]] = []

            raw_lines = spool_file.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in raw_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                next_retry = int(rec.get("next_retry_epoch", 0))
                if next_retry and next_retry > epoch_now():
                    unresolved.append(rec)
                    continue

                totals["processed"] += 1
                if self._breaker_open(state, provider):
                    totals["skipped"] += 1
                    rec["next_retry_epoch"] = epoch_now() + self._next_backoff(1)
                    unresolved.append(rec)
                    continue
                if not endpoint:
                    totals["skipped"] += 1
                    unresolved.append(rec)
                    continue

                key = self._attempt_key(rec)
                try:
                    response = self._send(endpoint, {"id": rec.get("id"), "input": rec.get("message", "")})
                    append_jsonl(
                        self.outbox_dir / f"{provider}_model_outbox.jsonl",
                        {
                            "ts_utc": utc_now(),
                            "provider": provider,
                            "request_id": rec.get("id", ""),
                            "response": response,
                        },
                    )
                    self._breaker_ok(state, provider)
                    attempts.pop(key, None)
                    totals["sent"] += 1
                    append_jsonl(self.bridge_events, {"ts_utc": utc_now(), "event": "worker_sent", "provider": provider})
                except (urllib.error.URLError, TimeoutError) as exc:
                    prev = int(attempts.get(key, 0))
                    cur = prev + 1
                    attempts[key] = cur
                    self._breaker_fail(state, provider)
                    totals["failed"] += 1
                    if cur >= self.max_attempts:
                        append_jsonl(
                            self.dead_letter_file,
                            {
                                "ts_utc": utc_now(),
                                "provider": provider,
                                "record": rec,
                                "error": str(exc),
                                "attempts": cur,
                            },
                        )
                        attempts.pop(key, None)
                        totals["dead"] += 1
                        append_jsonl(self.bridge_events, {"ts_utc": utc_now(), "event": "worker_dead_letter", "provider": provider})
                    else:
                        rec["last_error"] = str(exc)
                        rec["next_retry_epoch"] = epoch_now() + self._next_backoff(cur)
                        unresolved.append(rec)
                        append_jsonl(self.bridge_events, {"ts_utc": utc_now(), "event": "worker_retry", "provider": provider, "attempt": cur})

            spool_file.write_text(
                "".join(json.dumps(item, ensure_ascii=True) + "\n" for item in unresolved),
                encoding="utf-8",
            )

        self.save_state(state)
        return {"status": "ok", "ts_utc": utc_now(), **totals}


def run_loop(worker: ModelDeliveryWorker, interval_sec: int) -> None:
    while True:
        result = worker.run_once()
        print(json.dumps(result, ensure_ascii=True))
        time.sleep(interval_sec)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM model spool delivery worker.")
    parser.add_argument("--once", action="store_true", help="Run one worker iteration.")
    parser.add_argument("--interval-sec", type=int, default=5, help="Loop interval in seconds.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    worker = ModelDeliveryWorker(repo_root)
    if args.once:
        print(json.dumps(worker.run_once(), ensure_ascii=True, indent=2))
        return 0
    run_loop(worker, args.interval_sec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

