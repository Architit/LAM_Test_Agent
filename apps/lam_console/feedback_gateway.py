#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


class FeedbackGateway:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.external_mesh_state = self.hub_root / "external_provider_mesh_state.json"
        self.governance_state = self.hub_root / "governance_autopilot_state.json"
        self.security_state = self.hub_root / "security_telemetry_state.json"
        self.failsafe_state = self.hub_root / "failsafe_guard_state.json"
        self.power_state = self.hub_root / "power_fabric_state.json"
        self.lockdown_file = self.hub_root / "security_lockdown.flag"
        self.failsafe_active_file = self.hub_root / "failsafe_active.flag"

        self.events_file = self.bridge_root / "events.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.requests_file = self.bridge_root / "feedback_requests.jsonl"
        self.receipts_file = self.bridge_root / "feedback_dispatch_receipts.jsonl"
        self.spool_file = self.hub_root / "feedback_dispatch_spool.jsonl"
        self.state_file = self.hub_root / "feedback_gateway_state.json"
        self.channels_dir = self.bridge_root / "external_feedback"
        self.channels_dir.mkdir(parents=True, exist_ok=True)
        allowed_raw = os.getenv(
            "LAM_FEEDBACK_CRITICAL_ALLOWED",
            "openai,claude_sonnet,grok_xai,shinkai,github,google,microsoft",
        )
        self.critical_allowed = sorted({x.strip() for x in allowed_raw.split(",") if x.strip()})

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _ready_channels(self) -> list[str]:
        mesh = load_json(self.external_mesh_state, {})
        providers = mesh.get("providers", []) if isinstance(mesh, dict) else []
        out: list[str] = []
        for p in providers:
            if not isinstance(p, dict):
                continue
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            if p.get("ready") is True:
                out.append(name)
        return sorted(set(out))

    def _recommended_feedback(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        gov = load_json(self.governance_state, {})
        if isinstance(gov, dict):
            degraded = int(gov.get("domains_degraded", 0) or 0)
            if degraded > 0:
                out.append(
                    {
                        "source": "governance_autopilot",
                        "severity": "warning",
                        "message": f"governance domains degraded={degraded}; apply corrective vectors",
                        "targets": ["openai", "claude_sonnet", "grok_xai", "shinkai", "github"],
                    }
                )
        sec = load_json(self.security_state, {})
        if isinstance(sec, dict) and sec.get("overall_ok") is False:
            out.append(
                {
                    "source": "security_guard",
                    "severity": "critical",
                    "message": "security telemetry overall_ok=false; containment and remediation required",
                    "targets": ["openai", "claude_sonnet", "grok_xai", "shinkai", "github", "google", "microsoft"],
                }
            )
        fs = load_json(self.failsafe_state, {})
        if isinstance(fs, dict) and fs.get("active") is True:
            reasons = fs.get("critical_reasons", [])
            text = ",".join(reasons[:4]) if isinstance(reasons, list) else "unknown"
            out.append(
                {
                    "source": "failsafe_guard",
                    "severity": "critical",
                    "message": f"failsafe active; reasons={text}; keep circulation restricted",
                    "targets": ["openai", "claude_sonnet", "grok_xai", "shinkai", "github", "google", "microsoft"],
                }
            )
        power = load_json(self.power_state, {})
        if isinstance(power, dict):
            mode = str(power.get("mode", "")).strip()
            if mode == "turbo_peak":
                out.append(
                    {
                        "source": "power_fabric_guard",
                        "severity": "info",
                        "message": "power mode turbo_peak; prioritize critical compute and defer non-critical sync",
                        "targets": ["openai", "claude_sonnet", "grok_xai", "shinkai"],
                    }
                )
        return out

    def _load_requests(self) -> list[dict[str, Any]]:
        if not self.requests_file.exists():
            return []
        lines = self.requests_file.read_text(encoding="utf-8", errors="replace").splitlines()
        self.requests_file.write_text("", encoding="utf-8")
        out: list[dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
        return out

    @staticmethod
    def _event_id(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _dispatch(self, item: dict[str, Any], ready: list[str]) -> tuple[int, int]:
        targets = item.get("targets", [])
        if not isinstance(targets, list):
            targets = []
        targets = [str(x).strip() for x in targets if str(x).strip()]
        if not targets:
            targets = ready
        event_id = self._event_id(item)
        severity = str(item.get("severity", "info")).strip().lower()
        lockdown_active = self.lockdown_file.exists() or self.failsafe_active_file.exists()
        if lockdown_active and severity != "critical":
            self._append_jsonl(
                self.spool_file,
                {
                    "ts_utc": utc_now(),
                    "event_id": event_id,
                    "reason": "blocked_by_safety_gate",
                    "item": item,
                },
            )
            return 0, 1
        if lockdown_active and severity == "critical":
            targets = [t for t in targets if t in self.critical_allowed]
        sent = 0
        for provider in targets:
            if provider not in ready:
                continue
            outbox = self.channels_dir / f"{provider}.jsonl"
            envelope = {
                "ts_utc": utc_now(),
                "event_id": event_id,
                "provider": provider,
                "severity": severity,
                "source": item.get("source", "feedback_gateway"),
                "message": item.get("message", ""),
                "payload": item.get("payload", {}),
            }
            self._append_jsonl(outbox, envelope)
            self._append_jsonl(self.receipts_file, {"ts_utc": envelope["ts_utc"], "event_id": event_id, "provider": provider, "ok": True})
            sent += 1
        if sent == 0:
            self._append_jsonl(self.spool_file, {"ts_utc": utc_now(), "event_id": event_id, "reason": "no_ready_targets", "item": item})
            return 0, 1
        return sent, 0

    def run_once(self) -> dict[str, Any]:
        ready = self._ready_channels()
        generated = self._recommended_feedback()
        requested = self._load_requests()
        queue = generated + requested
        sent_total = 0
        spooled_total = 0
        for item in queue:
            sent, spooled = self._dispatch(item, ready=ready)
            sent_total += sent
            spooled_total += spooled

        payload = {
            "ts_utc": utc_now(),
            "ready_channels": ready,
            "lockdown_active": self.lockdown_file.exists() or self.failsafe_active_file.exists(),
            "critical_allowed_channels": self.critical_allowed,
            "generated_count": len(generated),
            "requested_count": len(requested),
            "sent_count": sent_total,
            "spooled_count": spooled_total,
            "signals": {
                "status": "ok" if spooled_total == 0 else "degraded",
                "feedback_pressure": round(float(spooled_total) / max(1, len(queue)), 4),
            },
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._append_jsonl(self.events_file, {"ts_utc": payload["ts_utc"], "event": "feedback_gateway_cycle", "sent": sent_total, "spooled": spooled_total})
        self._append_jsonl(self.audit_stream_file, {"ts_utc": payload["ts_utc"], "source": "feedback_gateway", "payload": payload})
        return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Autopilot external feedback/recommendation gateway.")
    p.add_argument("--once", action="store_true")
    p.add_argument("--interval-sec", type=int, default=20)
    return p


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = FeedbackGateway(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        out = svc.run_once()
        print(json.dumps({"ts_utc": out.get("ts_utc"), "sent": out.get("sent_count"), "spooled": out.get("spooled_count")}, ensure_ascii=True))
        time.sleep(max(5, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
