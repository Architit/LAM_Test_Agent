#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from apps.lam_console.core import LocalHubCore
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from apps.lam_console.core import LocalHubCore


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RoleOrchestrator:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub = LocalHubCore(repo_root)
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.registry_file = self.hub_root / "role_registry.json"
        self.profiles_file = repo_root / "infra" / "security" / "role_profiles.json"
        self.selector_file = repo_root / "infra" / "security" / "role_selector.json"
        self.profile_override_file = self.hub_root / "role_profile.override"
        self.state_file = self.hub_root / "role_orchestrator_state.json"
        self.counters_file = self.hub_root / "role_orchestrator_counters.json"
        self.hold_file = self.hub_root / "role_orchestrator_hold.flag"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.wake_events_file = self.bridge_root / "wake_events.jsonl"
        self.events_file = self.bridge_root / "events.jsonl"
        self.lockdown_file = self.hub_root / "security_lockdown.flag"
        self.sleep_threshold_sec = int(os.getenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "25"))
        self.device_profile = os.getenv("LAM_DEVICE_PROFILE", "portable_core")
        self.strict_secure_gate = os.getenv("LAM_WAKE_STRICT_SECURE_GATE", "0") in {"1", "true", "True"}
        self.degrade_on_battery = os.getenv("LAM_ROLE_DEGRADE_ON_BATTERY", "1") in {"1", "true", "True"}
        self.max_load_before_degrade = float(os.getenv("LAM_ROLE_MAX_LOAD_BEFORE_DEGRADE", "16"))
        self.max_temp_before_degrade_c = float(os.getenv("LAM_ROLE_MAX_TEMP_BEFORE_DEGRADE_C", "82"))
        self.reason_hold_threshold = int(os.getenv("LAM_ROLE_REASON_HOLD_THRESHOLD", "3"))
        self.security_state_file = self.hub_root / "security_telemetry_state.json"
        self.last_monotonic = time.monotonic()

        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.ensure_registry()
        self.ensure_profiles()
        self.ensure_selector()

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _emit_audit(self, payload: dict[str, Any]) -> None:
        event = {"ts_utc": utc_now(), "source": "role_orchestrator", **payload}
        self._append_jsonl(self.audit_stream_file, event)

    def ensure_registry(self) -> None:
        if self.registry_file.exists():
            return
        default_registry = {
            "roles": [
                {"role": "captain", "agent": "operator-agent", "priority": "p0"},
                {"role": "security_sentinel", "agent": "gemini-agent", "priority": "p0"},
                {"role": "memory_archivist", "agent": "archivator-agent", "priority": "p1"},
                {"role": "model_dispatcher", "agent": "codex-agent", "priority": "p1"},
            ]
        }
        self.registry_file.write_text(json.dumps(default_registry, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def ensure_profiles(self) -> None:
        if self.profiles_file.exists():
            return
        self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
        defaults = {
            "default_profile": "portable_core",
            "profiles": {
                "portable_core": {
                    "wake_actions": ["rebind_roles", "gws_health", "gws_sync_pull", "run_queue"],
                    "max_queue_jobs": 20,
                },
                "edge_gateway": {
                    "wake_actions": ["rebind_roles", "gws_health", "run_queue"],
                    "max_queue_jobs": 10,
                },
                "critical_lifeline": {
                    "wake_actions": ["rebind_roles", "gws_health", "gws_sync_pull", "run_queue"],
                    "max_queue_jobs": 50,
                },
            },
        }
        self.profiles_file.write_text(json.dumps(defaults, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def ensure_selector(self) -> None:
        if self.selector_file.exists():
            return
        self.selector_file.parent.mkdir(parents=True, exist_ok=True)
        defaults = {
            "default_profile": "portable_core",
            "rules": [
                {"match": {"node_type": "server"}, "profile": "critical_lifeline"},
                {"match": {"node_type": "edge"}, "profile": "edge_gateway"},
                {"match": {"hostname_regex": ".*laptop.*"}, "profile": "portable_core"},
            ],
        }
        self.selector_file.write_text(json.dumps(defaults, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def load_registry(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.registry_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"roles": []}
        if not isinstance(payload, dict):
            return {"roles": []}
        roles = payload.get("roles", [])
        if not isinstance(roles, list):
            roles = []
        return {"roles": [x for x in roles if isinstance(x, dict)]}

    def load_profile(self) -> tuple[str, dict[str, Any]]:
        try:
            payload = json.loads(self.profiles_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        profiles = payload.get("profiles", {}) if isinstance(payload, dict) else {}
        if not isinstance(profiles, dict):
            profiles = {}
        profile_name = self.device_profile
        if not profile_name:
            profile_name = self.select_profile_by_node(payload if isinstance(payload, dict) else {})
        if self.profile_override_file.exists():
            override = self.profile_override_file.read_text(encoding="utf-8", errors="replace").strip()
            if override:
                profile_name = override
        if profile_name not in profiles:
            profile_name = str(payload.get("default_profile", "portable_core"))
        profile = profiles.get(profile_name, {})
        if not isinstance(profile, dict):
            profile = {}
        return profile_name, profile

    @staticmethod
    def _detect_node_type() -> str:
        raw = os.getenv("LAM_NODE_TYPE", "").strip().lower()
        if raw in {"portable", "server", "edge"}:
            return raw
        host = os.uname().nodename.lower()
        if any(k in host for k in ("srv", "server")):
            return "server"
        if any(k in host for k in ("edge", "gateway")):
            return "edge"
        return "portable"

    def select_profile_by_node(self, payload: dict[str, Any]) -> str:
        try:
            selector = json.loads(self.selector_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            selector = {}
        node_type = self._detect_node_type()
        hostname = os.uname().nodename.lower()
        rules = selector.get("rules", []) if isinstance(selector, dict) else []
        if isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                match = rule.get("match", {})
                profile = str(rule.get("profile", "")).strip()
                if not isinstance(match, dict) or not profile:
                    continue
                rule_node_type = str(match.get("node_type", "")).strip().lower()
                if rule_node_type and rule_node_type != node_type:
                    continue
                host_regex = str(match.get("hostname_regex", "")).strip()
                if host_regex:
                    import re

                    if re.fullmatch(host_regex, hostname) is None:
                        continue
                return profile
        return str(selector.get("default_profile", "portable_core"))

    @staticmethod
    def _read_first_int(path: Path) -> int | None:
        try:
            return int(path.read_text(encoding="utf-8", errors="replace").strip())
        except Exception:
            return None

    def hardware_snapshot(self) -> dict[str, Any]:
        on_ac = None
        for ac_file in Path("/sys/class/power_supply").glob("AC*/online"):
            val = self._read_first_int(ac_file)
            if val is not None:
                on_ac = bool(val == 1)
                break

        battery_present = False
        for bat_file in Path("/sys/class/power_supply").glob("BAT*/present"):
            val = self._read_first_int(bat_file)
            if val is not None and val == 1:
                battery_present = True
                break

        max_temp_c = None
        for temp_file in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
            val = self._read_first_int(temp_file)
            if val is None:
                continue
            temp_c = float(val) / 1000.0 if val > 1000 else float(val)
            if max_temp_c is None or temp_c > max_temp_c:
                max_temp_c = temp_c

        try:
            load1, _, _ = os.getloadavg()
        except OSError:
            load1 = 0.0

        return {
            "on_ac_power": on_ac,
            "battery_present": battery_present,
            "max_temp_c": max_temp_c,
            "load1": float(load1),
        }

    def secure_posture_ok(self) -> bool:
        if not self.security_state_file.exists():
            return False
        try:
            payload = json.loads(self.security_state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        checks = payload.get("checks", {})
        if not isinstance(checks, dict):
            return False
        secure_ok = checks.get("secure_boot_ok")
        if isinstance(secure_ok, bool):
            return secure_ok
        telemetry = payload.get("telemetry", {})
        if isinstance(telemetry, dict):
            sb = telemetry.get("secure_boot_enabled")
            if isinstance(sb, bool):
                return sb
        return False

    def resolve_runtime_profile(self, lockdown: bool) -> tuple[str, dict[str, Any], list[str], dict[str, Any]]:
        profile_name, profile = self.load_profile()
        reasons: list[str] = []
        hw = self.hardware_snapshot()
        load1 = float(hw.get("load1", 0.0))
        temp_c = hw.get("max_temp_c")
        on_ac = hw.get("on_ac_power")

        if self.degrade_on_battery and on_ac is False and profile_name != "critical_lifeline":
            profile_name = "edge_gateway"
            reasons.append("battery_degrade")
        if load1 >= self.max_load_before_degrade and profile_name not in {"critical_lifeline", "critical_lifeline_degraded"}:
            profile_name = "edge_gateway"
            reasons.append("high_load_degrade")
        if isinstance(temp_c, (int, float)) and float(temp_c) >= self.max_temp_before_degrade_c:
            if profile_name == "critical_lifeline":
                profile_name = "critical_lifeline_degraded"
            elif profile_name != "critical_lifeline_degraded":
                profile_name = "edge_gateway"
            reasons.append("thermal_degrade")

        # Reload selected profile payload after dynamic reassignment.
        try:
            profiles_payload = json.loads(self.profiles_file.read_text(encoding="utf-8"))
            profiles = profiles_payload.get("profiles", {})
            if isinstance(profiles, dict):
                candidate = profiles.get(profile_name, {})
                if isinstance(candidate, dict):
                    profile = candidate
        except json.JSONDecodeError:
            pass

        if lockdown:
            reasons.append("security_lockdown")
        return profile_name, profile, reasons, hw

    def _load_counters(self) -> dict[str, int]:
        if not self.counters_file.exists():
            return {}
        try:
            payload = json.loads(self.counters_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        out: dict[str, int] = {}
        for k, v in payload.items():
            if isinstance(v, int):
                out[k] = v
        return out

    def _save_counters(self, counters: dict[str, int]) -> None:
        self.counters_file.write_text(json.dumps(counters, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def apply_runbooks(self, wake_event: dict[str, Any]) -> dict[str, Any]:
        reasons = wake_event.get("reason_codes", [])
        if not isinstance(reasons, list):
            reasons = []
        counters = self._load_counters()
        for reason in reasons:
            key = str(reason).strip()
            if not key:
                continue
            counters[key] = int(counters.get(key, 0)) + 1
        if not reasons:
            counters = {}
        self._save_counters(counters)

        hold_activated = False
        escalated = False
        trigger_reason = ""
        for reason, count in counters.items():
            if count >= self.reason_hold_threshold:
                hold_activated = True
                trigger_reason = reason
                break

        if hold_activated:
            hold_payload = {
                "ts_utc": utc_now(),
                "hold": True,
                "trigger_reason": trigger_reason,
                "threshold": self.reason_hold_threshold,
                "counters": counters,
            }
            was_active = self.hold_file.exists()
            self.hold_file.write_text(json.dumps(hold_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
            if not was_active:
                msg = (
                    f"role-orchestrator hold activated; reason={trigger_reason}; "
                    f"threshold={self.reason_hold_threshold}; counters={counters}"
                )
                if self.hub.send_agent("operator-agent", msg).ok:
                    escalated = True
            self._emit_audit(
                {
                    "event": "role_hold_activated",
                    "trigger_reason": trigger_reason,
                    "threshold": self.reason_hold_threshold,
                    "counters": counters,
                }
            )
        else:
            if self.hold_file.exists():
                self.hold_file.unlink(missing_ok=True)

        return {
            "hold_activated": hold_activated,
            "escalated": escalated,
            "trigger_reason": trigger_reason,
            "counters": counters,
        }

    def detect_wake(self, monotonic_now: float | None = None) -> tuple[bool, float]:
        now = monotonic_now if monotonic_now is not None else time.monotonic()
        gap = float(now - self.last_monotonic)
        self.last_monotonic = now
        return gap >= float(self.sleep_threshold_sec), gap

    def on_wake(self, gap_sec: float) -> dict[str, Any]:
        registry = self.load_registry()
        roles = registry.get("roles", [])
        lockdown = self.lockdown_file.exists()
        profile_name, profile, reason_codes, hw = self.resolve_runtime_profile(lockdown=lockdown)
        actions = profile.get("wake_actions", [])
        if not isinstance(actions, list):
            actions = []
        max_jobs = int(profile.get("max_queue_jobs", 20))

        wake_id = f"wake_{int(time.time())}"
        sent = 0
        strict_secure_blocked = self.strict_secure_gate and not self.secure_posture_ok()
        if strict_secure_blocked:
            reason_codes.append("strict_secure_gate_blocked")
        hold_active = self.hold_file.exists()
        if hold_active:
            reason_codes.append("role_orchestrator_hold_active")

        if not lockdown and not strict_secure_blocked and not hold_active and "rebind_roles" in actions:
            for role in roles:
                agent = str(role.get("agent", "")).strip()
                role_name = str(role.get("role", "")).strip() or "unknown"
                if not agent:
                    continue
                msg = (
                    f"role-rebind after device wake; role={role_name}; wake_id={wake_id}; profile={profile_name}; "
                    f"apply realtime security gates and resume orchestration"
                )
                res = self.hub.send_agent(agent, msg)
                if res.ok:
                    sent += 1
        if not lockdown and not strict_secure_blocked and not hold_active and "gws_health" in actions:
            self.hub.queue_gws("health")
        if not lockdown and not strict_secure_blocked and not hold_active and "gws_sync_pull" in actions:
            self.hub.queue_gws("sync_pull")
        if not lockdown and not strict_secure_blocked and not hold_active and "run_queue" in actions:
            self.hub.run_queue(max_jobs=max_jobs)
        bridge = self.hub.bridge_status().payload

        event = {
            "ts_utc": utc_now(),
            "event": "device_wake_detected",
            "wake_id": wake_id,
            "profile": profile_name,
            "gap_sec": round(gap_sec, 3),
            "roles_notified": sent,
            "roles_total": len(roles),
            "lockdown": lockdown,
            "strict_secure_blocked": strict_secure_blocked,
            "hold_active": hold_active,
            "reason_codes": reason_codes,
        }
        runbook = self.apply_runbooks(event)
        self._append_jsonl(self.wake_events_file, event)
        self._append_jsonl(self.events_file, event)
        self._emit_audit({"event": "device_wake_detected", "wake": event, "runbook": runbook})

        out = {
            "ts_utc": utc_now(),
            "wake": event,
            "runbook": runbook,
            "profile": {"name": profile_name, "actions": actions, "max_queue_jobs": max_jobs},
            "hardware": hw,
            "bridge": {
                "queue_items": bridge.get("queue_items", 0),
                "security_lockdown": bridge.get("security_lockdown", False),
            },
        }
        self.state_file.write_text(json.dumps(out, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return out

    def run_cycle(self, monotonic_now: float | None = None) -> dict[str, Any]:
        is_wake, gap = self.detect_wake(monotonic_now=monotonic_now)
        if is_wake:
            return self.on_wake(gap_sec=gap)
        payload = {
            "ts_utc": utc_now(),
            "event": "tick",
            "wake_detected": False,
            "gap_sec": round(gap, 3),
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM realtime role orchestrator with wake rebind.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=5)
    parser.add_argument("--force-wake", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)

    if args.force_wake:
        orch.last_monotonic = 0.0

    if args.once:
        print(json.dumps(orch.run_cycle(), ensure_ascii=True))
        return 0

    while True:
        payload = orch.run_cycle()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "wake_detected": bool(payload.get("wake"))}, ensure_ascii=True))
        time.sleep(max(1, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
