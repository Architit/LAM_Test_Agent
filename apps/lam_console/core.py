from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shlex
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_lam_gateway_module(repo_root: Path):
    script = repo_root / "scripts" / "lam_gateway.py"
    spec = importlib.util.spec_from_file_location("lam_gateway", script)
    if not spec or not spec.loader:
        raise RuntimeError(f"lam_gateway module loader unavailable: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class CommandResult:
    ok: bool
    title: str
    payload: dict[str, Any]


class LocalHubCore:
    """Captain-bridge local control plane. No CLI transit required."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.gateway = _load_lam_gateway_module(repo_root)
        self.gateway.ensure_state()
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.inbox_dir = self.hub_root / "inbox"
        self.outbox_dir = self.hub_root / "outbox"
        self.spool_dir = self.hub_root / "model_spool"
        self.dead_letter_file = self.hub_root / "dead_letter.jsonl"
        self.worker_state_file = self.hub_root / "worker_state.json"
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.bridge_events = self.bridge_root / "events.jsonl"
        self.bridge_commands = self.bridge_root / "commands.jsonl"
        self.bridge_status_file = self.bridge_root / "status.json"
        self.gws_requests_file = self.bridge_root / "gws_requests.jsonl"
        self.gws_results_file = self.bridge_root / "gws_results.jsonl"
        self.gates_dir = self.bridge_root / "gates"
        self.devices_file = self.bridge_root / "devices.json"
        self.device_inbox_dir = self.bridge_root / "device_inbox"
        self.device_outbox_dir = self.bridge_root / "device_outbox"
        self.mcp_watchdog_state_file = self.hub_root / "mcp_watchdog_state.json"
        self.gws_bridge_state_file = self.hub_root / "gws_bridge_state.json"
        self.security_telemetry_state_file = self.hub_root / "security_telemetry_state.json"
        self.security_lockdown_file = self.hub_root / "security_lockdown.flag"
        self.role_orchestrator_state_file = self.hub_root / "role_orchestrator_state.json"
        self.power_fabric_state_file = self.hub_root / "power_fabric_state.json"
        self.device_mesh_state_file = self.hub_root / "device_mesh_state.json"
        self.activity_telemetry_state_file = self.hub_root / "activity_telemetry_state.json"
        self.ambient_light_state_file = self.hub_root / "ambient_light_state.json"
        self.io_spectral_state_file = self.hub_root / "io_spectral_state.json"
        self.governance_autopilot_state_file = self.hub_root / "governance_autopilot_state.json"
        self.media_sync_state_file = self.hub_root / "media_stream_sync_state.json"
        self.rootkey_gate_state_file = self.hub_root / "rootkey_gate_state.json"
        self.failsafe_state_file = self.hub_root / "failsafe_guard_state.json"
        self.feedback_gateway_state_file = self.hub_root / "feedback_gateway_state.json"

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.gates_dir.mkdir(parents=True, exist_ok=True)
        self.device_inbox_dir.mkdir(parents=True, exist_ok=True)
        self.device_outbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.devices_file.exists():
            self.devices_file.write_text(json.dumps({"devices": []}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def known_agents(self) -> list[str]:
        env_agents = [x.strip() for x in os.getenv("LAM_CONSOLE_AGENTS", "").split(",") if x.strip()]
        if env_agents:
            return sorted(set(env_agents))
        defaults = ["codex-agent", "gemini-agent", "operator-agent", "archivator-agent"]
        inbox_names = [p.stem for p in self.inbox_dir.glob("*.jsonl")]
        outbox_names = [p.stem for p in self.outbox_dir.glob("*.jsonl")]
        return sorted(set(defaults + inbox_names + outbox_names))

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _gateway_cmd_json(self, func_name: str, **kwargs: Any) -> dict[str, Any]:
        func = getattr(self.gateway, func_name)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            rc = func(SimpleNamespace(**kwargs))
        raw = stream.getvalue().strip()
        payload: dict[str, Any] = {"rc": rc}
        if raw.startswith("{") and raw.endswith("}"):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload["raw"] = raw
        elif raw:
            payload["raw"] = raw
        return payload

    @staticmethod
    def _tail_jsonl(path: Path, limit: int = 40) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed = {"raw": line}
            if isinstance(parsed, dict):
                out.append(parsed)
        return out

    def health(self) -> CommandResult:
        payload = self._gateway_cmd_json("cmd_health", json=True)
        return CommandResult(ok=True, title="health", payload=payload)

    def route(self, data_class: str, size_bytes: int | None = None) -> CommandResult:
        payload = self._gateway_cmd_json("cmd_route", data_class=data_class, size_bytes=size_bytes)
        return CommandResult(ok=True, title="route", payload=payload)

    def enqueue_put(self, src: str, data_class: str = "generic") -> CommandResult:
        payload = self._gateway_cmd_json(
            "cmd_enqueue_put",
            src=str(Path(src).resolve()),
            data_class=data_class,
            provider="",
            name="",
        )
        ok = bool(payload.get("status") == "ok")
        self._append_jsonl(
            self.bridge_events,
            {"ts_utc": _utc_now(), "event": "enqueue_put", "ok": ok, "payload": payload},
        )
        return CommandResult(ok=ok, title="enqueue-put", payload=payload)

    def run_queue(self, max_jobs: int = 20) -> CommandResult:
        payload = self._gateway_cmd_json("cmd_run_queue", max_jobs=max_jobs)
        ok = bool(payload.get("status") == "ok")
        self._append_jsonl(
            self.bridge_events,
            {"ts_utc": _utc_now(), "event": "run_queue", "ok": ok, "payload": payload},
        )
        return CommandResult(ok=ok, title="run-queue", payload=payload)

    def send_agent(self, agent: str, message: str) -> CommandResult:
        if not agent or not message:
            return CommandResult(ok=False, title="send", payload={"error": "agent and message required"})
        line = {"ts_utc": _utc_now(), "agent": agent, "message": message, "source": "lam_console"}
        target = self.inbox_dir / f"{agent}.jsonl"
        self._append_jsonl(target, line)
        self._append_jsonl(self.bridge_commands, {"ts_utc": _utc_now(), "type": "agent_send", "target": agent, "message": message})
        self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "agent_message_queued", "agent": agent})
        return CommandResult(ok=True, title="send", payload={"status": "queued", "file": str(target), "event": line})

    def send_model(self, provider: str, message: str, timeout_sec: int = 30) -> CommandResult:
        endpoint_map = {
            "codex": os.getenv("LAM_CODEX_ENDPOINT", "").strip(),
            "gemini": os.getenv("LAM_GEMINI_ENDPOINT", "").strip(),
        }
        provider = provider.lower().strip()
        endpoint = endpoint_map.get(provider, "")
        if provider not in endpoint_map:
            return CommandResult(ok=False, title="model", payload={"error": f"unknown provider: {provider}"})

        envelope = {
            "id": f"model_{provider}_{hashlib.sha256(f'{_utc_now()}:{message}'.encode('utf-8')).hexdigest()[:12]}",
            "ts_utc": _utc_now(),
            "provider": provider,
            "message": message,
        }
        self._append_jsonl(self.bridge_commands, {"ts_utc": _utc_now(), "type": "model_send", "target": provider, "message": message})

        if not endpoint:
            envelope["status"] = "spooled_no_endpoint"
            target = self.spool_dir / f"{provider}.jsonl"
            self._append_jsonl(target, envelope)
            self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "model_spooled", "provider": provider, "reason": "endpoint_not_configured"})
            return CommandResult(ok=False, title="model", payload={"error": "endpoint_not_configured", "spooled": str(target)})

        body = json.dumps({"id": envelope["id"], "input": message}).encode("utf-8")
        request = urllib.request.Request(endpoint, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                raw = response.read().decode("utf-8", errors="replace")
                parsed = {"raw": raw}
                if raw.startswith("{") and raw.endswith("}"):
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        pass
                out = {"provider": provider, "response": parsed}
                self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "model_sent", "provider": provider, "ok": True})
                return CommandResult(ok=True, title="model", payload=out)
        except urllib.error.URLError as exc:
            envelope["status"] = "spooled_transport_error"
            envelope["error"] = str(exc)
            target = self.spool_dir / f"{provider}.jsonl"
            self._append_jsonl(target, envelope)
            self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "model_spooled", "provider": provider, "reason": str(exc)})
            return CommandResult(ok=False, title="model", payload={"provider": provider, "error": str(exc), "spooled": str(target)})

    def bridge_status(self) -> CommandResult:
        queue = self._gateway_cmd_json("cmd_queue_list")
        worker = {}
        if self.worker_state_file.exists():
            worker = json.loads(self.worker_state_file.read_text(encoding="utf-8"))
        mcp = {}
        if self.mcp_watchdog_state_file.exists():
            mcp = json.loads(self.mcp_watchdog_state_file.read_text(encoding="utf-8"))
        gws = {}
        if self.gws_bridge_state_file.exists():
            gws = json.loads(self.gws_bridge_state_file.read_text(encoding="utf-8"))
        security = {}
        if self.security_telemetry_state_file.exists():
            security = json.loads(self.security_telemetry_state_file.read_text(encoding="utf-8"))
        roles = {}
        if self.role_orchestrator_state_file.exists():
            roles = json.loads(self.role_orchestrator_state_file.read_text(encoding="utf-8"))
        power = {}
        if self.power_fabric_state_file.exists():
            power = json.loads(self.power_fabric_state_file.read_text(encoding="utf-8"))
        mesh = {}
        if self.device_mesh_state_file.exists():
            mesh = json.loads(self.device_mesh_state_file.read_text(encoding="utf-8"))
        activity = {}
        if self.activity_telemetry_state_file.exists():
            activity = json.loads(self.activity_telemetry_state_file.read_text(encoding="utf-8"))
        ambient = {}
        if self.ambient_light_state_file.exists():
            ambient = json.loads(self.ambient_light_state_file.read_text(encoding="utf-8"))
        io_spectral = {}
        if self.io_spectral_state_file.exists():
            io_spectral = json.loads(self.io_spectral_state_file.read_text(encoding="utf-8"))
        governance_autopilot = {}
        if self.governance_autopilot_state_file.exists():
            governance_autopilot = json.loads(self.governance_autopilot_state_file.read_text(encoding="utf-8"))
        media_sync = {}
        if self.media_sync_state_file.exists():
            media_sync = json.loads(self.media_sync_state_file.read_text(encoding="utf-8"))
        rootkey_gate = {}
        if self.rootkey_gate_state_file.exists():
            rootkey_gate = json.loads(self.rootkey_gate_state_file.read_text(encoding="utf-8"))
        failsafe = {}
        if self.failsafe_state_file.exists():
            failsafe = json.loads(self.failsafe_state_file.read_text(encoding="utf-8"))
        feedback_gateway = {}
        if self.feedback_gateway_state_file.exists():
            feedback_gateway = json.loads(self.feedback_gateway_state_file.read_text(encoding="utf-8"))
        payload = {
            "ts_utc": _utc_now(),
            "agents": self.known_agents(),
            "spool_files": sorted(str(p.name) for p in self.spool_dir.glob("*.jsonl")),
            "gates": self.list_gates(),
            "devices": self.list_devices(),
            "dead_letter_exists": self.dead_letter_file.exists(),
            "queue_items": len(queue.get("items", [])) if isinstance(queue, dict) else 0,
            "bridge_events_tail": self._tail_jsonl(self.bridge_events, limit=12),
            "worker": worker,
            "mcp_watchdog": mcp,
            "gws_bridge": gws,
            "security_telemetry": security,
            "security_lockdown": self.security_lockdown_file.exists(),
            "role_orchestrator": roles,
            "power_fabric": power,
            "device_mesh": mesh,
            "activity_telemetry": activity,
            "ambient_light": ambient,
            "io_spectral": io_spectral,
            "governance_autopilot": governance_autopilot,
            "media_sync": media_sync,
            "rootkey_gate": rootkey_gate,
            "failsafe_guard": failsafe,
            "feedback_gateway": feedback_gateway,
        }
        self.bridge_status_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return CommandResult(ok=True, title="bridge-status", payload=payload)

    def queue_gws(self, op: str, **kwargs: Any) -> CommandResult:
        payload: dict[str, Any] = {"id": f"gws_{hashlib.sha256(f'{_utc_now()}:{op}:{kwargs}'.encode('utf-8')).hexdigest()[:12]}", "op": op}
        payload.update(kwargs)
        self._append_jsonl(self.gws_requests_file, payload)
        self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "gws_request_queued", "op": op, "id": payload["id"]})
        return CommandResult(ok=True, title="gws", payload={"status": "queued", "request": payload, "requests_file": str(self.gws_requests_file)})

    def pane_snapshot(self, pane: str) -> list[str]:
        pane = pane.upper()
        if pane == "AGENTS":
            lines = [f"- {x}" for x in self.known_agents()]
            if not lines:
                lines = ["(no agents discovered)"]
            return lines
        if pane == "QUEUE":
            queue = self._gateway_cmd_json("cmd_queue_list")
            items = queue.get("items", []) if isinstance(queue, dict) else []
            out = [f"queue_items={len(items)}"]
            for item in items[-30:]:
                out.append(
                    f"{item.get('id','?')} type={item.get('type')} status={item.get('status')} attempts={item.get('attempts')}"
                )
            return out or ["(queue empty)"]
        if pane == "MODELS":
            out = []
            for file in sorted(self.spool_dir.glob("*.jsonl")):
                count = len(file.read_text(encoding="utf-8", errors="replace").splitlines())
                out.append(f"{file.name}: pending={count}")
            if self.dead_letter_file.exists():
                dead = len(self.dead_letter_file.read_text(encoding="utf-8", errors="replace").splitlines())
                out.append(f"dead_letter: {dead}")
            return out or ["(model spool empty)"]
        if pane == "BRIDGE":
            events = self._tail_jsonl(self.bridge_events, limit=30)
            if not events:
                return ["(bridge events empty)"]
            out = []
            for item in events:
                out.append(f"{item.get('ts_utc','?')} {item.get('event', item.get('type','event'))}")
            return out
        if pane == "GATES":
            gates = self.list_gates()
            if not gates:
                return ["(no gates) use: open-gate windows|linux|macos"]
            out = []
            for gate in gates:
                out.append(
                    f"{gate.get('name','?')} target={gate.get('target_os','?')} endpoint={gate.get('endpoint','')}"
                )
            return out
        if pane == "DEVICES":
            devices = self.list_devices()
            if not devices:
                return ["(no devices) use: register-device <id> <type> <platform> [endpoint]"]
            out = []
            for d in devices:
                out.append(
                    f"{d.get('device_id')} type={d.get('device_type')} platform={d.get('platform')} endpoint={d.get('endpoint','')}"
                )
            return out
        if pane == "POWER":
            if not self.power_fabric_state_file.exists():
                return ["(power state empty) run: scripts/lam_power_fabric_guard.sh --once"]
            try:
                payload = json.loads(self.power_fabric_state_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return ["(power state parse error)"]
            tele = payload.get("telemetry", {}) if isinstance(payload, dict) else {}
            return [
                f"mode={payload.get('mode','unknown')} manual_profile={payload.get('manual_profile','auto')}",
                f"cpu load1={tele.get('load1','?')} ratio={tele.get('load_ratio','?')}",
                f"mem_available_mb={tele.get('mem_available_mb','?')} swap_used_pct={tele.get('swap_used_pct','?')}",
                f"iowait_pct={tele.get('iowait_pct','?')} fan_rpm_max={tele.get('fan_rpm_max','?')}",
                f"gpu={tele.get('gpu',{}).get('available',False)} ts={payload.get('ts_utc','?')}",
            ]
        if pane == "MESH":
            lines: list[str] = []
            if self.device_mesh_state_file.exists():
                try:
                    mesh = json.loads(self.device_mesh_state_file.read_text(encoding="utf-8"))
                    lines.append(
                        f"mesh dispatched={mesh.get('dispatched','?')} dir={mesh.get('direction','?')} ts={mesh.get('ts_utc','?')}"
                    )
                except json.JSONDecodeError:
                    lines.append("mesh state parse error")
            else:
                lines.append("(mesh state empty) run: scripts/lam_device_mesh_daemon.sh --once")
            devices = self.list_devices()
            lines.append(f"registered_devices={len(devices)}")
            if self.ambient_light_state_file.exists():
                try:
                    ambient = json.loads(self.ambient_light_state_file.read_text(encoding="utf-8"))
                    lines.append(
                        f"ambient dispatched={ambient.get('dispatched','?')} mode={ambient.get('vector_mode','?')} ts={ambient.get('ts_utc','?')}"
                    )
                except json.JSONDecodeError:
                    lines.append("ambient state parse error")
            for d in devices[-8:]:
                lines.append(
                    f"{d.get('device_id')} transport={d.get('transport','legacy')} trust={d.get('trust_level','legacy')} scopes={','.join(d.get('scopes',[])) if isinstance(d.get('scopes',[]), list) else ''}"
                )
            return lines
        if pane == "ACTIVITY":
            if not self.activity_telemetry_state_file.exists():
                return ["(activity telemetry empty) run: scripts/lam_activity_telemetry.sh --once"]
            try:
                payload = json.loads(self.activity_telemetry_state_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return ["(activity telemetry parse error)"]
            sig = payload.get("signals", {}) if isinstance(payload, dict) else {}
            act = payload.get("activity", {}) if isinstance(payload, dict) else {}
            db = payload.get("databases", {}) if isinstance(payload, dict) else {}
            archives = payload.get("archives", {}) if isinstance(payload, dict) else {}
            lines = [
                f"activity_score={sig.get('activity_score','?')} ts={payload.get('ts_utc','?')}",
                f"bridge_events_5m={act.get('bridge_events_5m','?')} bridge_commands_5m={act.get('bridge_commands_5m','?')}",
                f"routing_events_60m={act.get('routing_events_60m','?')} runtime_events_60m={act.get('runtime_events_60m','?')}",
                f"background_errors_60m={act.get('background_errors_60m','?')}",
                f"db_count={db.get('count','?')} db_bytes_total={db.get('bytes_total','?')}",
                f"archive_bytes_total={sig.get('archive_bytes_total','?')}",
            ]
            if self.io_spectral_state_file.exists():
                try:
                    spectral = json.loads(self.io_spectral_state_file.read_text(encoding="utf-8"))
                    s_sig = spectral.get("signals", {}) if isinstance(spectral, dict) else {}
                    lat = spectral.get("latency", {}) if isinstance(spectral, dict) else {}
                    vec = spectral.get("io_vector", {}) if isinstance(spectral, dict) else {}
                    lines.append(
                        "io_spectral pressure={p} dominant={d} events={e}".format(
                            p=s_sig.get("spectral_pressure", "?"),
                            d=s_sig.get("dominant_domain", "?"),
                            e=s_sig.get("io_event_count_window", "?"),
                        )
                    )
                    lines.append(
                        "latency p50/p95/max ms={}/{}/{}".format(
                            lat.get("p50_ms", "?"),
                            lat.get("p95_ms", "?"),
                            lat.get("max_ms", "?"),
                        )
                    )
                    lines.append(
                        "vector low/mid/high={}/{}/{}".format(
                            vec.get("low_0_5_2hz", "?"),
                            vec.get("mid_2_8hz", "?"),
                            vec.get("high_8_32hz", "?"),
                        )
                    )
                except json.JSONDecodeError:
                    lines.append("io_spectral parse error")
            else:
                lines.append("(io spectral empty) run: scripts/lam_io_spectral.sh --once")
            if self.governance_autopilot_state_file.exists():
                try:
                    gov = json.loads(self.governance_autopilot_state_file.read_text(encoding="utf-8"))
                    gsig = gov.get("signals", {}) if isinstance(gov, dict) else {}
                    lines.append(
                        "gov_autopilot status={s} pressure={p} degraded={d}/{t}".format(
                            s=gsig.get("autopilot_status", "?"),
                            p=gsig.get("governance_pressure", "?"),
                            d=gov.get("domains_degraded", "?"),
                            t=gov.get("domains_total", "?"),
                        )
                    )
                except json.JSONDecodeError:
                    lines.append("governance_autopilot parse error")
            else:
                lines.append("(governance autopilot empty) run: scripts/lam_governance_autopilot.sh --once")
            if self.media_sync_state_file.exists():
                try:
                    ms = json.loads(self.media_sync_state_file.read_text(encoding="utf-8"))
                    sig = ms.get("signals", {}) if isinstance(ms, dict) else {}
                    lines.append(
                        "media_sync mode={m} applied/planned={a}/{p} conflicts={c}".format(
                            m=ms.get("mode", "?"),
                            a=ms.get("applied_ops", "?"),
                            p=ms.get("planned_ops", "?"),
                            c=ms.get("conflict_ops", "?"),
                        )
                    )
                    lines.append(
                        "media_sync pressure sync/lock={}/{} status={}".format(
                            sig.get("sync_pressure", "?"),
                            sig.get("lock_pressure", "?"),
                            sig.get("status", "?"),
                        )
                    )
                except json.JSONDecodeError:
                    lines.append("media_sync parse error")
            else:
                lines.append("(media sync empty) run: scripts/lam_media_sync.sh --once")
            if self.rootkey_gate_state_file.exists():
                try:
                    rk = json.loads(self.rootkey_gate_state_file.read_text(encoding="utf-8"))
                    lines.append(
                        "rootkey active={} mode={} reason={}".format(
                            rk.get("active", False),
                            rk.get("mode", "inactive"),
                            rk.get("reason", ""),
                        )
                    )
                except json.JSONDecodeError:
                    lines.append("rootkey_gate parse error")
            else:
                lines.append("(rootkey gate empty) run: scripts/lam_rootkey_gate.sh --once")
            if self.failsafe_state_file.exists():
                try:
                    fs = json.loads(self.failsafe_state_file.read_text(encoding="utf-8"))
                    lines.append(
                        "failsafe active={} critical={} reasons={}".format(
                            fs.get("active", False),
                            fs.get("critical", False),
                            ",".join(fs.get("critical_reasons", [])[:3]),
                        )
                    )
                except json.JSONDecodeError:
                    lines.append("failsafe_guard parse error")
            else:
                lines.append("(failsafe empty) run: scripts/lam_failsafe_guard.sh --once")
            if self.feedback_gateway_state_file.exists():
                try:
                    fb = json.loads(self.feedback_gateway_state_file.read_text(encoding="utf-8"))
                    lines.append(
                        "feedback sent/spooled={}/{} status={}".format(
                            fb.get("sent_count", "?"),
                            fb.get("spooled_count", "?"),
                            fb.get("signals", {}).get("status", "?"),
                        )
                    )
                except json.JSONDecodeError:
                    lines.append("feedback_gateway parse error")
            else:
                lines.append("(feedback gateway empty) run: scripts/lam_feedback_gateway.sh --once")
            for k, v in archives.items():
                if isinstance(v, dict):
                    lines.append(f"{k}: files={v.get('files','?')} bytes={v.get('bytes','?')}")
            return lines
        return ["(unknown pane)"]

    def list_gates(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for file in sorted(self.gates_dir.glob("*.json")):
            try:
                payload = json.loads(file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                out.append(payload)
        return out

    def open_gate(self, target_os: str, endpoint: str = "") -> CommandResult:
        target = target_os.strip().lower()
        if target not in {"windows", "linux", "macos"}:
            return CommandResult(ok=False, title="open-gate", payload={"error": "target_os must be windows|linux|macos"})

        if not endpoint:
            endpoint = os.getenv("LAM_PORTAL_ENDPOINT", "http://127.0.0.1:8765")

        gate_name = f"gate_{target}"
        payload = {
            "name": gate_name,
            "target_os": target,
            "endpoint": endpoint,
            "created_utc": _utc_now(),
            "bridge_root": str(self.bridge_root),
            "inbox_dir": str(self.inbox_dir),
            "outbox_dir": str(self.outbox_dir),
            "spool_dir": str(self.spool_dir),
        }
        file = self.gates_dir / f"{gate_name}.json"
        file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "gate_opened", "target_os": target, "endpoint": endpoint})
        return CommandResult(ok=True, title="open-gate", payload=payload)

    def list_devices(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.devices_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        devices = payload.get("devices", [])
        if not isinstance(devices, list):
            return []
        return [d for d in devices if isinstance(d, dict)]

    def register_device(self, device_id: str, device_type: str, platform: str, endpoint: str = "") -> CommandResult:
        device_id = device_id.strip().lower()
        if not device_id:
            return CommandResult(ok=False, title="register-device", payload={"error": "device_id required"})
        platform = platform.strip().lower()
        allowed_platforms = {"android", "ios", "watchos", "wearos", "earbuds", "other"}
        if platform not in allowed_platforms:
            return CommandResult(
                ok=False,
                title="register-device",
                payload={"error": f"platform must be one of: {','.join(sorted(allowed_platforms))}"},
            )
        devices = self.list_devices()
        now = _utc_now()
        existing = next((d for d in devices if d.get("device_id") == device_id), None)
        if existing:
            existing["device_type"] = device_type
            existing["platform"] = platform
            existing["endpoint"] = endpoint
            existing["updated_utc"] = now
            action = "updated"
        else:
            devices.append(
                {
                    "device_id": device_id,
                    "device_type": device_type,
                    "platform": platform,
                    "endpoint": endpoint,
                    "created_utc": now,
                    "updated_utc": now,
                }
            )
            action = "registered"
        self.devices_file.write_text(json.dumps({"devices": devices}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._append_jsonl(self.bridge_events, {"ts_utc": now, "event": "device_registered", "device_id": device_id, "platform": platform})
        return CommandResult(ok=True, title="register-device", payload={"status": action, "device_id": device_id})

    def send_device(self, device_id: str, message: str) -> CommandResult:
        device_id = device_id.strip().lower()
        if not device_id:
            return CommandResult(ok=False, title="send-device", payload={"error": "device_id required"})
        if not message:
            return CommandResult(ok=False, title="send-device", payload={"error": "message required"})
        devices = self.list_devices()
        device = next((d for d in devices if d.get("device_id") == device_id), None)
        if not device:
            return CommandResult(ok=False, title="send-device", payload={"error": f"device not found: {device_id}"})
        envelope = {
            "ts_utc": _utc_now(),
            "device_id": device_id,
            "platform": device.get("platform", ""),
            "message": message,
            "status": "queued",
        }
        self._append_jsonl(self.device_outbox_dir / f"{device_id}.jsonl", envelope)
        self._append_jsonl(self.bridge_events, {"ts_utc": _utc_now(), "event": "device_message_queued", "device_id": device_id})
        return CommandResult(ok=True, title="send-device", payload={"status": "queued", "device_id": device_id})

    def execute(self, line: str) -> CommandResult:
        line = line.strip()
        if not line:
            return CommandResult(ok=True, title="noop", payload={})
        parts = shlex.split(line)
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in {"help", "?"}:
            return CommandResult(
                ok=True,
                title="help",
                payload={
                    "commands": [
                        "help",
                        "agents",
                        "health",
                        "route <class> [size_bytes]",
                        "send <agent> <message>",
                        "model <codex|gemini> <message>",
                        "enqueue-put <path> [class]",
                        "run-queue [max_jobs]",
                        "bridge-status",
                        "open-gate <windows|linux|macos> [endpoint]",
                        "list-gates",
                        "register-device <id> <type> <platform> [endpoint]",
                        "list-devices",
                        "send-device <id> <message>",
                        "mcp-status",
                        "gws-health",
                        "gws-sync <push|pull>",
                        "gws-list [prefix] [limit]",
                        "quit",
                    ]
                },
            )
        if cmd == "agents":
            return CommandResult(ok=True, title="agents", payload={"agents": self.known_agents()})
        if cmd == "health":
            return self.health()
        if cmd == "route":
            if not args:
                return CommandResult(ok=False, title="route", payload={"error": "route <class> [size_bytes]"})
            data_class = args[0]
            size = int(args[1]) if len(args) > 1 else None
            return self.route(data_class, size)
        if cmd == "send":
            if len(args) < 2:
                return CommandResult(ok=False, title="send", payload={"error": "send <agent> <message>"})
            return self.send_agent(args[0], " ".join(args[1:]))
        if cmd == "model":
            if len(args) < 2:
                return CommandResult(ok=False, title="model", payload={"error": "model <codex|gemini> <message>"})
            return self.send_model(args[0], " ".join(args[1:]))
        if cmd == "enqueue-put":
            if not args:
                return CommandResult(ok=False, title="enqueue-put", payload={"error": "enqueue-put <path> [class]"})
            data_class = args[1] if len(args) > 1 else "generic"
            return self.enqueue_put(args[0], data_class)
        if cmd == "run-queue":
            max_jobs = int(args[0]) if args else 20
            return self.run_queue(max_jobs)
        if cmd == "bridge-status":
            return self.bridge_status()
        if cmd == "open-gate":
            if not args:
                return CommandResult(ok=False, title="open-gate", payload={"error": "open-gate <windows|linux|macos> [endpoint]"})
            endpoint = args[1] if len(args) > 1 else ""
            return self.open_gate(args[0], endpoint)
        if cmd == "list-gates":
            return CommandResult(ok=True, title="list-gates", payload={"gates": self.list_gates()})
        if cmd == "register-device":
            if len(args) < 3:
                return CommandResult(
                    ok=False,
                    title="register-device",
                    payload={"error": "register-device <id> <type> <platform> [endpoint]"},
                )
            endpoint = args[3] if len(args) > 3 else ""
            return self.register_device(args[0], args[1], args[2], endpoint)
        if cmd == "list-devices":
            return CommandResult(ok=True, title="list-devices", payload={"devices": self.list_devices()})
        if cmd == "send-device":
            if len(args) < 2:
                return CommandResult(ok=False, title="send-device", payload={"error": "send-device <id> <message>"})
            return self.send_device(args[0], " ".join(args[1:]))
        if cmd == "mcp-status":
            if not self.mcp_watchdog_state_file.exists():
                return CommandResult(ok=False, title="mcp-status", payload={"error": "mcp watchdog state is not available yet"})
            payload = json.loads(self.mcp_watchdog_state_file.read_text(encoding="utf-8"))
            return CommandResult(ok=True, title="mcp-status", payload=payload)
        if cmd == "gws-health":
            return self.queue_gws("health")
        if cmd == "gws-sync":
            if not args or args[0] not in {"push", "pull"}:
                return CommandResult(ok=False, title="gws-sync", payload={"error": "gws-sync <push|pull>"})
            return self.queue_gws("sync_push" if args[0] == "push" else "sync_pull")
        if cmd == "gws-list":
            prefix = args[0] if args else ""
            limit = int(args[1]) if len(args) > 1 else 100
            return self.queue_gws("list", prefix=prefix, limit=limit)
        if cmd in {"quit", "exit"}:
            return CommandResult(ok=True, title="quit", payload={"quit": True})

        return CommandResult(ok=False, title=cmd, payload={"error": f"unknown command: {cmd}"})
