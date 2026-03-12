#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_scopes(raw: str) -> list[str]:
    scopes = [x.strip().lower() for x in raw.split(",") if x.strip()]
    allowed = {
        "telemetry_read",
        "files_exchange",
        "audio_control",
        "input_control",
        "notifications",
        "device_status",
        "test_reports",
        "ambient_light",
        "full_data_access",
    }
    for scope in scopes:
        if scope not in allowed:
            raise RuntimeError(f"unsupported scope: {scope}")
    return sorted(set(scopes))


class DeviceMeshCtl:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.devices_file = self.bridge_root / "devices.json"
        self.events_file = self.bridge_root / "events.jsonl"
        self.mesh_queue_file = self.bridge_root / "device_mesh_queue.jsonl"
        self.device_outbox_dir = self.bridge_root / "device_outbox"
        self.device_outbox_dir.mkdir(parents=True, exist_ok=True)
        if not self.devices_file.exists():
            self.devices_file.write_text(json.dumps({"devices": []}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _load_devices(self) -> list[dict[str, Any]]:
        payload = json.loads(self.devices_file.read_text(encoding="utf-8"))
        devices = payload.get("devices", [])
        return [d for d in devices if isinstance(d, dict)]

    def _save_devices(self, devices: list[dict[str, Any]]) -> None:
        self.devices_file.write_text(json.dumps({"devices": devices}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def pair(self, device_id: str, device_type: str, platform: str, transport: str, scopes: list[str], endpoint: str) -> dict[str, Any]:
        transport = transport.lower().strip()
        if transport not in {"wifi", "bluetooth", "hybrid", "usb"}:
            raise RuntimeError("transport must be wifi|bluetooth|hybrid|usb")
        devices = self._load_devices()
        now = utc_now()
        existing = next((d for d in devices if d.get("device_id") == device_id), None)
        payload = {
            "device_id": device_id,
            "device_type": device_type,
            "platform": platform,
            "endpoint": endpoint,
            "transport": transport,
            "scopes": scopes,
            "consent": {"approved": True, "approved_utc": now},
            "verification": {"passed": False, "verified_utc": ""},
            "authentication": {"passed": False, "authenticated_utc": ""},
            "trust_level": "discovery",
            "created_utc": now,
            "updated_utc": now,
        }
        if existing:
            existing.update(payload)
            action = "updated"
        else:
            devices.append(payload)
            action = "paired"
        self._save_devices(devices)
        self._append_jsonl(self.events_file, {"ts_utc": now, "event": "device_mesh_pair", "device_id": device_id, "transport": transport, "scopes": scopes})
        return {"status": action, "device_id": device_id}

    def pair_profile(self, profile: str, device_id: str, endpoint: str) -> dict[str, Any]:
        p = profile.strip().lower()
        presets: dict[str, dict[str, Any]] = {
            "windows_asus": {
                "device_type": "laptop",
                "platform": "other",
                "transport": "wifi",
                "scopes": ["telemetry_read", "files_exchange", "device_status", "test_reports", "ambient_light"],
            },
            "windows_razer": {
                "device_type": "laptop",
                "platform": "other",
                "transport": "hybrid",
                "scopes": ["telemetry_read", "files_exchange", "input_control", "device_status", "test_reports", "ambient_light"],
            },
            "samsung_android": {
                "device_type": "phone",
                "platform": "android",
                "transport": "wifi",
                "scopes": ["telemetry_read", "files_exchange", "notifications", "device_status", "test_reports"],
            },
            "google_android": {
                "device_type": "phone",
                "platform": "android",
                "transport": "wifi",
                "scopes": ["telemetry_read", "files_exchange", "notifications", "device_status", "test_reports"],
            },
            "earbuds_bluetooth": {
                "device_type": "earbuds",
                "platform": "earbuds",
                "transport": "bluetooth",
                "scopes": ["audio_control", "device_status"],
            },
            "pointer_bluetooth": {
                "device_type": "pointer",
                "platform": "other",
                "transport": "bluetooth",
                "scopes": ["input_control", "device_status"],
            },
            "ambient_rgb": {
                "device_type": "peripheral",
                "platform": "other",
                "transport": "usb",
                "scopes": ["ambient_light", "device_status"],
            },
        }
        if p not in presets:
            raise RuntimeError(f"unknown profile: {profile}")
        preset = presets[p]
        return self.pair(
            device_id=device_id,
            device_type=str(preset["device_type"]),
            platform=str(preset["platform"]),
            transport=str(preset["transport"]),
            scopes=[str(x) for x in preset["scopes"]],
            endpoint=endpoint,
        )

    def grant(self, device_id: str, scopes: list[str]) -> dict[str, Any]:
        devices = self._load_devices()
        now = utc_now()
        target = next((d for d in devices if d.get("device_id") == device_id), None)
        if not target:
            raise RuntimeError(f"device not found: {device_id}")
        target["scopes"] = scopes
        target["consent"] = {"approved": True, "approved_utc": now}
        target.setdefault("verification", {"passed": False, "verified_utc": ""})
        target.setdefault("authentication", {"passed": False, "authenticated_utc": ""})
        if target.get("trust_level") not in {"verified_full", "trusted"}:
            target["trust_level"] = "limited"
        target["updated_utc"] = now
        self._save_devices(devices)
        self._append_jsonl(self.events_file, {"ts_utc": now, "event": "device_mesh_grant", "device_id": device_id, "scopes": scopes})
        return {"status": "granted", "device_id": device_id}

    def revoke(self, device_id: str) -> dict[str, Any]:
        devices = self._load_devices()
        now = utc_now()
        target = next((d for d in devices if d.get("device_id") == device_id), None)
        if not target:
            raise RuntimeError(f"device not found: {device_id}")
        target["consent"] = {"approved": False, "revoked_utc": now}
        target["scopes"] = []
        target["trust_level"] = "discovery"
        target["updated_utc"] = now
        self._save_devices(devices)
        self._append_jsonl(self.events_file, {"ts_utc": now, "event": "device_mesh_revoke", "device_id": device_id})
        return {"status": "revoked", "device_id": device_id}

    @staticmethod
    def _scope_paths(repo_root: Path, scopes: list[str]) -> list[str]:
        mapping = {
            "telemetry_read": [".gateway/hub/security_telemetry_state.json", ".gateway/hub/power_fabric_state.json"],
            "files_exchange": [".gateway/exchange"],
            "test_reports": [".gateway/test_runs/background/errors.jsonl", ".gateway/circulation/inversion/inbox"],
            "device_status": [".gateway/bridge/captain/status.json"],
            "ambient_light": [".gateway/bridge/captain/ambient_light_vector.json"],
        }
        out: list[str] = []
        for scope in scopes:
            for rel in mapping.get(scope, []):
                p = repo_root / rel
                if p.exists():
                    out.append(str(p))
        return sorted(set(out))

    def promote_full_access(self, device_id: str) -> dict[str, Any]:
        devices = self._load_devices()
        now = utc_now()
        target = next((d for d in devices if d.get("device_id") == device_id), None)
        if not target:
            raise RuntimeError(f"device not found: {device_id}")
        consent = target.get("consent", {})
        if not isinstance(consent, dict) or not consent.get("approved"):
            raise RuntimeError("device consent is not approved")
        target["verification"] = {"passed": True, "verified_utc": now}
        target["authentication"] = {"passed": True, "authenticated_utc": now}
        scopes = [str(x) for x in target.get("scopes", []) if isinstance(x, str)]
        if "full_data_access" not in scopes:
            scopes.append("full_data_access")
        target["scopes"] = sorted(set(scopes))
        target["trust_level"] = "verified_full"
        target["updated_utc"] = now
        self._save_devices(devices)
        self._append_jsonl(
            self.events_file,
            {
                "ts_utc": now,
                "event": "device_mesh_promote_full_access",
                "device_id": device_id,
                "trust_level": "verified_full",
            },
        )
        return {"status": "promoted", "device_id": device_id, "trust_level": "verified_full"}

    def sync_once(self, target: str, direction: str) -> dict[str, Any]:
        direction = direction.lower().strip()
        if direction not in {"push", "pull", "bidirectional"}:
            raise RuntimeError("direction must be push|pull|bidirectional")
        devices = self._load_devices()
        now = utc_now()
        selected = devices if target == "all" else [d for d in devices if d.get("device_id") == target]
        dispatched = 0
        for device in selected:
            consent = device.get("consent", {})
            if not isinstance(consent, dict) or not consent.get("approved"):
                continue
            scopes = [str(x) for x in device.get("scopes", []) if isinstance(x, str)]
            trust_level = str(device.get("trust_level", "discovery"))
            full_access = ("full_data_access" in scopes) and trust_level == "verified_full"
            paths = self._scope_paths(self.repo_root, scopes)
            if full_access:
                paths = [str(self.repo_root)]
            manifest = {
                "ts_utc": now,
                "op": "mesh_sync",
                "direction": direction,
                "device_id": device.get("device_id"),
                "transport": device.get("transport", ""),
                "scopes": scopes,
                "trust_level": trust_level,
                "full_access": full_access,
                "paths": paths,
            }
            self._append_jsonl(self.mesh_queue_file, manifest)
            outbox = self.device_outbox_dir / f"{device.get('device_id')}.jsonl"
            self._append_jsonl(outbox, manifest)
            dispatched += 1
        self._append_jsonl(self.events_file, {"ts_utc": now, "event": "device_mesh_sync_dispatched", "target": target, "direction": direction, "count": dispatched})
        return {"status": "ok", "target": target, "direction": direction, "dispatched": dispatched}

    def list_devices(self) -> dict[str, Any]:
        return {"devices": self._load_devices()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Device mesh control (Wi-Fi/Bluetooth hybrid orchestration).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pair = sub.add_parser("pair")
    p_pair.add_argument("device_id")
    p_pair.add_argument("device_type")
    p_pair.add_argument("platform")
    p_pair.add_argument("transport")
    p_pair.add_argument("scopes")
    p_pair.add_argument("--endpoint", default="")

    p_pair_profile = sub.add_parser("pair-profile")
    p_pair_profile.add_argument("profile")
    p_pair_profile.add_argument("device_id")
    p_pair_profile.add_argument("--endpoint", default="")

    p_grant = sub.add_parser("grant")
    p_grant.add_argument("device_id")
    p_grant.add_argument("scopes")

    p_revoke = sub.add_parser("revoke")
    p_revoke.add_argument("device_id")

    p_promote = sub.add_parser("promote-full-access")
    p_promote.add_argument("device_id")

    p_sync = sub.add_parser("sync-once")
    p_sync.add_argument("target", nargs="?", default="all")
    p_sync.add_argument("direction", nargs="?", default="bidirectional")

    sub.add_parser("list")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    ctl = DeviceMeshCtl(repo_root)
    if args.cmd == "pair":
        result = ctl.pair(
            device_id=args.device_id.strip().lower(),
            device_type=args.device_type.strip().lower(),
            platform=args.platform.strip().lower(),
            transport=args.transport.strip().lower(),
            scopes=parse_scopes(args.scopes),
            endpoint=args.endpoint.strip(),
        )
    elif args.cmd == "grant":
        result = ctl.grant(args.device_id.strip().lower(), parse_scopes(args.scopes))
    elif args.cmd == "pair-profile":
        result = ctl.pair_profile(
            args.profile.strip().lower(),
            args.device_id.strip().lower(),
            args.endpoint.strip(),
        )
    elif args.cmd == "revoke":
        result = ctl.revoke(args.device_id.strip().lower())
    elif args.cmd == "promote-full-access":
        result = ctl.promote_full_access(args.device_id.strip().lower())
    elif args.cmd == "sync-once":
        result = ctl.sync_once(args.target.strip().lower(), args.direction.strip().lower())
    else:
        result = ctl.list_devices()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
