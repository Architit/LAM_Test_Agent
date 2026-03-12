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


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


class FailsafeGuard:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.gateway_state_dir = Path(os.getenv("LAM_GATEWAY_STATE_DIR", str(repo_root / ".gateway")))
        self.gateway_policy_file = Path(
            os.getenv("LAM_GATEWAY_POLICY_FILE", str(self.gateway_state_dir / "routing_policy.json"))
        )
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.gateway_policy_file.parent.mkdir(parents=True, exist_ok=True)

        self.security_state_file = self.hub_root / "security_telemetry_state.json"
        self.power_state_file = self.hub_root / "power_fabric_state.json"
        self.lockdown_file = self.hub_root / "security_lockdown.flag"
        self.events_file = self.bridge_root / "events.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.state_file = self.hub_root / "failsafe_guard_state.json"
        self.active_file = self.hub_root / "failsafe_active.flag"
        self.force_file = self.hub_root / "failsafe_force.flag"
        self.rollback_file = self.hub_root / "failsafe_rollback_request.json"
        self.role_override_file = self.hub_root / "role_profile.override"
        self.power_override_file = self.hub_root / "power_profile.override"
        self.role_hold_file = self.hub_root / "role_orchestrator_hold.flag"
        self.role_hold_owner = self.hub_root / "failsafe_role_hold.owner"
        self.ks_owner = self.hub_root / "failsafe_circulation_killswitch.owner"
        self.lockdown_owner = self.hub_root / "failsafe_lockdown.owner"

        self.activate_after = int(os.getenv("LAM_FAILSAFE_ACTIVATE_AFTER_CYCLES", "2"))
        self.recover_after = int(os.getenv("LAM_FAILSAFE_RECOVER_AFTER_CYCLES", "5"))
        self.auto_recover = os.getenv("LAM_FAILSAFE_AUTO_RECOVER", "1") in {"1", "true", "True"}
        self.role_profile = os.getenv("LAM_FAILSAFE_ROLE_PROFILE", "critical_lifeline")
        self.power_profile = os.getenv("LAM_FAILSAFE_POWER_PROFILE", "quiet")
        self.max_load_ratio = float(os.getenv("LAM_FAILSAFE_MAX_LOAD_RATIO", "0.95"))
        self.max_swap_pct = float(os.getenv("LAM_FAILSAFE_MAX_SWAP_USED_PCT", "60"))
        self.max_iowait_pct = float(os.getenv("LAM_FAILSAFE_MAX_IOWAIT_PCT", "25"))
        self.max_gpu_temp_c = float(os.getenv("LAM_FAILSAFE_MAX_GPU_TEMP_C", "90"))

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _emit_event(self, event: str, payload: dict[str, Any]) -> None:
        row = {"ts_utc": utc_now(), "event": event, **payload}
        self._append_jsonl(self.events_file, row)
        self._append_jsonl(self.audit_stream_file, {"ts_utc": row["ts_utc"], "source": "failsafe_guard", "payload": row})

    def _set_circulation_killswitch(self, on: bool) -> bool:
        policy = load_json(self.gateway_policy_file, {})
        if not isinstance(policy, dict):
            policy = {}
        circulation = policy.get("data_circulation", {})
        if not isinstance(circulation, dict):
            circulation = {}
        policy["data_circulation"] = circulation
        circulation["kill_switch"] = bool(on)
        write_json(self.gateway_policy_file, policy)
        return bool(circulation["kill_switch"])

    def _critical_reasons(self) -> tuple[list[str], dict[str, Any]]:
        reasons: list[str] = []
        security = load_json(self.security_state_file, {})
        power = load_json(self.power_state_file, {})

        sec_ok = bool(security.get("overall_ok", False))
        if not sec_ok:
            reasons.append("security_overall_not_ok")
        if self.lockdown_file.exists() and not self.lockdown_owner.exists():
            reasons.append("security_lockdown_active")
        if self.force_file.exists():
            reasons.append("failsafe_force_flag")

        tele = power.get("telemetry", {}) if isinstance(power, dict) else {}
        load_ratio = float(tele.get("load_ratio", 0.0) or 0.0)
        swap_used_pct = float(tele.get("swap_used_pct", 0.0) or 0.0)
        iowait_pct = float(tele.get("iowait_pct", 0.0) or 0.0)
        gpu_temp_c = None
        gpu = tele.get("gpu", {})
        if isinstance(gpu, dict) and gpu.get("available") is True:
            val = gpu.get("temp_c")
            if isinstance(val, (int, float)):
                gpu_temp_c = float(val)

        if load_ratio >= self.max_load_ratio:
            reasons.append("load_ratio_critical")
        if swap_used_pct >= self.max_swap_pct:
            reasons.append("swap_pressure_critical")
        if iowait_pct >= self.max_iowait_pct:
            reasons.append("iowait_critical")
        if isinstance(gpu_temp_c, float) and gpu_temp_c >= self.max_gpu_temp_c:
            reasons.append("gpu_temp_critical")

        metrics = {
            "security_overall_ok": sec_ok,
            "lockdown": self.lockdown_file.exists(),
            "load_ratio": round(load_ratio, 3),
            "swap_used_pct": round(swap_used_pct, 3),
            "iowait_pct": round(iowait_pct, 3),
            "gpu_temp_c": gpu_temp_c,
        }
        return reasons, metrics

    def _activate(self, reasons: list[str], metrics: dict[str, Any], counters: dict[str, int]) -> dict[str, Any]:
        self.role_override_file.write_text(self.role_profile + "\n", encoding="utf-8")
        self.power_override_file.write_text(self.power_profile + "\n", encoding="utf-8")
        if not self.role_hold_file.exists():
            hold_payload = {
                "ts_utc": utc_now(),
                "hold": True,
                "trigger_reason": "failsafe_guard",
                "threshold": self.activate_after,
                "counters": counters,
            }
            write_json(self.role_hold_file, hold_payload)
            self.role_hold_owner.write_text("failsafe_guard\n", encoding="utf-8")
        if not self.lockdown_file.exists():
            write_json(self.lockdown_file, {"ts_utc": utc_now(), "source": "failsafe_guard", "reasons": reasons})
            self.lockdown_owner.write_text("failsafe_guard\n", encoding="utf-8")
        self._set_circulation_killswitch(True)
        self.ks_owner.write_text("failsafe_guard\n", encoding="utf-8")
        rollback_payload = {"ts_utc": utc_now(), "requested_by": "failsafe_guard", "reasons": reasons, "metrics": metrics}
        write_json(self.rollback_file, rollback_payload)
        active_payload = {
            "ts_utc": utc_now(),
            "active": True,
            "profile": {"role": self.role_profile, "power": self.power_profile},
            "reasons": reasons,
            "metrics": metrics,
        }
        write_json(self.active_file, active_payload)
        self._emit_event("failsafe_activated", {"reasons": reasons, "metrics": metrics})
        return active_payload

    def _deactivate(self) -> None:
        if self.role_override_file.exists() and self.role_override_file.read_text(encoding="utf-8", errors="replace").strip() == self.role_profile:
            self.role_override_file.unlink(missing_ok=True)
        if self.power_override_file.exists() and self.power_override_file.read_text(encoding="utf-8", errors="replace").strip() == self.power_profile:
            self.power_override_file.unlink(missing_ok=True)
        if self.role_hold_owner.exists():
            self.role_hold_file.unlink(missing_ok=True)
            self.role_hold_owner.unlink(missing_ok=True)
        if self.ks_owner.exists():
            self._set_circulation_killswitch(False)
            self.ks_owner.unlink(missing_ok=True)
        if self.lockdown_owner.exists():
            self.lockdown_file.unlink(missing_ok=True)
            self.lockdown_owner.unlink(missing_ok=True)
        self.rollback_file.unlink(missing_ok=True)
        self.active_file.unlink(missing_ok=True)
        self.force_file.unlink(missing_ok=True)
        self._emit_event("failsafe_recovered", {"auto_recover": self.auto_recover})

    def run_once(self) -> dict[str, Any]:
        state = load_json(
            self.state_file,
            {"critical_cycles": 0, "stable_cycles": 0, "active": False, "last_transition_utc": "", "last_reasons": []},
        )
        if not isinstance(state, dict):
            state = {"critical_cycles": 0, "stable_cycles": 0, "active": False, "last_transition_utc": "", "last_reasons": []}
        counters_prev = state.get("counters", {})
        if isinstance(counters_prev, dict):
            if not isinstance(state.get("critical_cycles"), int):
                state["critical_cycles"] = int(counters_prev.get("critical_cycles", 0) or 0)
            if not isinstance(state.get("stable_cycles"), int):
                state["stable_cycles"] = int(counters_prev.get("stable_cycles", 0) or 0)
        reasons, metrics = self._critical_reasons()
        critical = bool(reasons)
        active = bool(state.get("active", False)) or self.active_file.exists()

        if critical:
            state["critical_cycles"] = int(state.get("critical_cycles", 0)) + 1
            state["stable_cycles"] = 0
            state["last_reasons"] = reasons
        else:
            state["stable_cycles"] = int(state.get("stable_cycles", 0)) + 1
            state["critical_cycles"] = 0
            state["last_reasons"] = []

        if not active and critical and int(state.get("critical_cycles", 0)) >= max(1, self.activate_after):
            self._activate(reasons=reasons, metrics=metrics, counters={"critical_cycles": int(state.get("critical_cycles", 0))})
            active = True
            state["active"] = True
            state["last_transition_utc"] = utc_now()
        elif active and (not critical) and self.auto_recover and int(state.get("stable_cycles", 0)) >= max(1, self.recover_after):
            self._deactivate()
            active = False
            state["active"] = False
            state["last_transition_utc"] = utc_now()
        else:
            state["active"] = active

        payload = {
            "ts_utc": utc_now(),
            "active": bool(state.get("active", False)),
            "critical": critical,
            "critical_reasons": reasons,
            "metrics": metrics,
            "counters": {
                "critical_cycles": int(state.get("critical_cycles", 0)),
                "stable_cycles": int(state.get("stable_cycles", 0)),
            },
            "policy": {
                "activate_after_cycles": self.activate_after,
                "recover_after_cycles": self.recover_after,
                "auto_recover": self.auto_recover,
                "role_profile": self.role_profile,
                "power_profile": self.power_profile,
            },
            "last_transition_utc": state.get("last_transition_utc", ""),
            "critical_cycles": int(state.get("critical_cycles", 0)),
            "stable_cycles": int(state.get("stable_cycles", 0)),
        }
        write_json(self.state_file, payload)
        self._emit_event("failsafe_cycle", {"active": payload["active"], "critical": critical, "reasons": reasons})
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM fail-safe guard for lifecycle and containment orchestration.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=8)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    guard = FailsafeGuard(repo_root)
    if args.once:
        print(json.dumps(guard.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = guard.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "active": payload.get("active"), "critical": payload.get("critical")}, ensure_ascii=True))
        time.sleep(max(2, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
