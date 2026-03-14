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


def safe_mtime(path: Path) -> float:
    try:
        return float(path.stat().st_mtime)
    except OSError:
        return 0.0


def build_domain_matrix(repo_root: Path) -> dict[str, list[Path]]:
    return {
        "protocoling": [
            repo_root / "infra/security/GATEWAY_SECURITY_PROTOCOL_V2.md",
            repo_root / "infra/security/LICENSE_COMPLIANCE_PROTOCOL_V1.md",
            repo_root / "infra/security/FAILSAFE_LIFESUPPORT_PROFILE_V1.md",
        ],
        "planning": [
            repo_root / "infra/governance/MASTER_PLAN_LIVE_CORRECTION_V0_1.md",
            repo_root / "ROADMAP.md",
        ],
        "analyzing": [
            repo_root / "infra/governance/ACTIVITY_TELEMETRY_PROTOCOL_V1.md",
            repo_root / "infra/governance/IO_SPECTRAL_ANALYSIS_PROTOCOL_V1.md",
        ],
        "strategizing": [
            repo_root / "infra/governance/DIRECTIVE_VECTOR_MAP.md",
            repo_root / "infra/governance/EMERGENCY_RUNBOOK.md",
        ],
        "contracting": [
            repo_root / "infra/governance/AGENT_CONTRACT_TEMPLATE.md",
            repo_root / "SYSTEM_STATE_CONTRACT.md",
            repo_root / "infra/governance/FAILSAFE_GOVERNANCE_CONTRACT_V1.md",
            repo_root / "infra/governance/STRUCTURAL_SYSTEMS_CONTRACTS_V1.md",
        ],
        "politizing": [
            repo_root / "infra/governance/GATEWAY_CIRCULATION_POLICY_TEMPLATE.json",
            repo_root / "infra/governance/CROSS_ORG_DATA_CIRCULATION_PROTOCOL.md",
            repo_root / "infra/governance/EXTERNAL_FEEDBACK_GATEWAY_PROTOCOL_V1.md",
        ],
        "instructing": [
            repo_root / "infra/security/AGENT_OPERATOR_INSTRUCTIONS.md",
            repo_root / "AGENTS.md",
        ],
        "revising": [
            repo_root / "infra/security/SECURITY_REVIEW_2026-03-07.md",
            repo_root / "DEV_LOGS.md",
        ],
        "licensing": [
            repo_root / "infra/security/LICENSE_COMPLIANCE_PROTOCOL_V1.md",
            repo_root / "infra/governance/LICENSE_AUDIT_REPORT_2026-03-07.json",
            repo_root / "infra/governance/LICENSE_BASELINE.json",
        ],
        "mapping": [
            repo_root / "TOPOLOGY_MAP.md",
            repo_root / "TERRITORY_MAP.md",
            repo_root / "infra/governance/STRUCTURAL_SYSTEMS_MAP_V1.md",
        ],
        "topologizing": [
            repo_root / "TOTAL_TOPOLOGY_VERIFICATION_PROTOCOL.md",
            repo_root / "WORKFLOW_SNAPSHOT_STATE.md",
        ],
        "chronologizing": [
            repo_root / "chronolog",
            repo_root / "journal",
            repo_root / "DEV_LOGS.md",
        ],
        "lifecycle_expansion": [
            repo_root / "infra/governance/LIFECYCLE_EXPANSION_SYSTEMS_V1.md",
            repo_root / "concept",
            repo_root / "design",
            repo_root / "realization",
            repo_root / "incarnation",
            repo_root / "imagination",
            repo_root / "creation",
            repo_root / "tvorion",
            repo_root / "generation",
            repo_root / "formation",
            repo_root / "selection",
            repo_root / "synthesis",
            repo_root / "creativation",
            repo_root / "hibernation",
            repo_root / "stasization",
            repo_root / "hydrogenation",
            repo_root / "aeranation",
        ],
    }


def evaluate_domain(paths: list[Path], now: float, stale_sec: int) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    exists_count = 0
    stale_count = 0
    for p in paths:
        exists = p.exists()
        exists_count += 1 if exists else 0
        mtime = safe_mtime(p) if exists else 0.0
        staleness = int(max(0.0, now - mtime)) if exists and mtime > 0 else None
        stale = bool(staleness is not None and staleness > stale_sec)
        stale_count += 1 if stale else 0
        entries.append(
            {
                "path": str(p),
                "exists": exists,
                "is_dir": p.is_dir() if exists else False,
                "staleness_sec": staleness,
                "stale": stale,
            }
        )
    coverage = round(float(exists_count) / max(1, len(paths)), 4)
    health = "ok"
    if exists_count < len(paths):
        health = "degraded_missing"
    elif stale_count > 0:
        health = "degraded_stale"
    return {
        "coverage": coverage,
        "stale_count": stale_count,
        "required_count": len(paths),
        "exists_count": exists_count,
        "health": health,
        "artifacts": entries,
    }


def corrective_vector(domain: str, status: dict[str, Any]) -> dict[str, Any]:
    if status.get("health") == "ok":
        return {"domain": domain, "action": "none", "priority": "P3"}
    missing = int(status.get("required_count", 0)) - int(status.get("exists_count", 0))
    if missing > 0:
        return {
            "domain": domain,
            "action": "materialize_missing_artifacts",
            "priority": "P1",
            "missing_count": missing,
        }
    return {
        "domain": domain,
        "action": "refresh_stale_artifacts",
        "priority": "P2",
        "stale_count": int(status.get("stale_count", 0)),
    }


class GovernanceAutopilot:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.state_file = self.hub_root / "governance_autopilot_state.json"
        self.timeline_file = self.hub_root / "governance_autopilot_timeline.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.events_file = self.bridge_root / "events.jsonl"
        self.stale_sec = int(os.getenv("LAM_GOV_AUTOPILOT_STALE_SEC", str(72 * 3600)))

    def run_once(self) -> dict[str, Any]:
        now = time.time()
        matrix = build_domain_matrix(self.repo_root)
        domains: dict[str, Any] = {}
        vectors: list[dict[str, Any]] = []
        degraded = 0
        for domain, paths in matrix.items():
            status = evaluate_domain(paths, now=now, stale_sec=self.stale_sec)
            domains[domain] = status
            vector = corrective_vector(domain, status)
            vectors.append(vector)
            if status.get("health") != "ok":
                degraded += 1
        payload = {
            "ts_utc": utc_now(),
            "stale_threshold_sec": self.stale_sec,
            "domains_total": len(domains),
            "domains_degraded": degraded,
            "domains_ok": len(domains) - degraded,
            "domains": domains,
            "corrective_vectors": vectors,
            "signals": {
                "governance_pressure": round(float(degraded) / max(1, len(domains)), 4),
                "autopilot_status": "ok" if degraded == 0 else "degraded",
            },
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        with self.timeline_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
        event = {
            "ts_utc": payload["ts_utc"],
            "event": "governance_autopilot_cycle",
            "domains_degraded": degraded,
            "governance_pressure": payload["signals"]["governance_pressure"],
        }
        with self.events_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")
        with self.audit_stream_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts_utc": payload["ts_utc"], "source": "governance_autopilot", "event": "snapshot", "payload": payload}, ensure_ascii=True) + "\n")
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance autopilot expansion daemon.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=30)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = GovernanceAutopilot(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = svc.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "degraded": payload.get("domains_degraded", 0), "pressure": payload.get("signals", {}).get("governance_pressure", 0.0)}, ensure_ascii=True))
        time.sleep(max(5, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
