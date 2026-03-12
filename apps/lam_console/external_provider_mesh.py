#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], timeout: float = 4.0) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as exc:
        return 99, "", str(exc)


def tcp_up(host: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class ExternalProviderMesh:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.state_file = self.hub_root / "external_provider_mesh_state.json"
        self.events_file = self.bridge_root / "events.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.devices_file = self.bridge_root / "devices.json"

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _provider_github(self) -> dict[str, Any]:
        rc, out, _ = run(["git", "-C", str(self.repo_root), "remote", "-v"])
        has_origin = "origin" in out
        has_gh = shutil.which("gh") is not None
        return {"name": "github", "ready": bool(rc == 0 and has_origin), "signals": {"git_remote_ok": rc == 0, "has_origin": has_origin, "gh_cli": has_gh}}

    def _provider_google(self) -> dict[str, Any]:
        gws_bin = shutil.which("gws") is not None or (Path.home() / ".local/bin/gws").exists()
        drive_root = os.getenv("LAM_GWS_DRIVE_ROOT", os.getenv("GATEWAY_GWORKSPACE_ROOT", "")).strip()
        drive_ok = bool(drive_root and Path(drive_root).exists())
        return {"name": "google", "ready": bool(gws_bin and drive_ok), "signals": {"gws_bin": gws_bin, "drive_root_configured": bool(drive_root), "drive_root_exists": drive_ok}}

    def _provider_microsoft(self) -> dict[str, Any]:
        one_root = os.getenv("GATEWAY_ONEDRIVE_ROOT", "").strip()
        root_ok = bool(one_root and Path(one_root).exists())
        return {"name": "microsoft", "ready": root_ok, "signals": {"onedrive_root_configured": bool(one_root), "onedrive_root_exists": root_ok}}

    def _provider_openai(self) -> dict[str, Any]:
        key = os.getenv("OPENAI_API_KEY", "").strip()
        return {"name": "openai", "ready": bool(key), "signals": {"api_key_present": bool(key)}}

    def _provider_claude_sonnet(self) -> dict[str, Any]:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return {"name": "claude_sonnet", "ready": bool(key), "signals": {"api_key_present": bool(key)}}

    def _provider_grok_xai(self) -> dict[str, Any]:
        key = os.getenv("XAI_API_KEY", "").strip()
        return {"name": "grok_xai", "ready": bool(key), "signals": {"api_key_present": bool(key)}}

    def _provider_shinkai(self) -> dict[str, Any]:
        url = os.getenv("SHINKAI_API_URL", "").strip()
        return {"name": "shinkai", "ready": bool(url), "signals": {"api_url_present": bool(url)}}

    def _provider_ollama(self) -> dict[str, Any]:
        ollama_bin = shutil.which("ollama") is not None
        ollama_tcp = tcp_up("127.0.0.1", int(os.getenv("OLLAMA_PORT", "11434")))
        return {"name": "ollama", "ready": bool(ollama_bin and ollama_tcp), "signals": {"ollama_bin": ollama_bin, "ollama_tcp_11434": ollama_tcp}}

    def _provider_nvidia(self) -> dict[str, Any]:
        bin_ok = shutil.which("nvidia-smi") is not None
        rc, _, _ = run(["nvidia-smi"]) if bin_ok else (1, "", "missing")
        return {"name": "nvidia", "ready": bool(bin_ok and rc == 0), "signals": {"nvidia_smi_bin": bin_ok, "nvidia_smi_ok": rc == 0}}

    def _provider_intel(self) -> dict[str, Any]:
        rc, out, _ = run(["lscpu"])
        txt = out.lower()
        ok = rc == 0 and ("intel" in txt or "genuineintel" in txt)
        return {"name": "intel", "ready": ok, "signals": {"lscpu_ok": rc == 0, "intel_detected": ok}}

    def _provider_amd(self) -> dict[str, Any]:
        rc, out, _ = run(["lscpu"])
        txt = out.lower()
        ok = rc == 0 and ("amd" in txt or "authenticamd" in txt)
        return {"name": "amd", "ready": ok, "signals": {"lscpu_ok": rc == 0, "amd_detected": ok}}

    def _load_devices(self) -> list[dict[str, Any]]:
        if not self.devices_file.exists():
            return []
        try:
            payload = json.loads(self.devices_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        devices = payload.get("devices", []) if isinstance(payload, dict) else []
        if not isinstance(devices, list):
            return []
        return [d for d in devices if isinstance(d, dict)]

    def _provider_razer(self) -> dict[str, Any]:
        devices = self._load_devices()
        has_profile = any(str(d.get("profile", "")).strip().lower() == "windows_razer" for d in devices)
        has_name_hint = any("razer" in str(d.get("device_id", "")).strip().lower() for d in devices)
        return {
            "name": "razer",
            "ready": bool(has_profile or has_name_hint),
            "signals": {"paired_profile_windows_razer": has_profile, "paired_razer_name_hint": has_name_hint},
        }

    def _provider_samsung_android(self) -> dict[str, Any]:
        devices = self._load_devices()
        has_profile = any(str(d.get("profile", "")).strip().lower() == "samsung_android" for d in devices)
        has_platform_android = any(str(d.get("platform", "")).strip().lower() == "android" for d in devices)
        has_name_hint = any("samsung" in str(d.get("device_id", "")).strip().lower() for d in devices)
        return {
            "name": "samsung_android",
            "ready": bool(has_profile or (has_platform_android and has_name_hint)),
            "signals": {
                "paired_profile_samsung_android": has_profile,
                "paired_platform_android": has_platform_android,
                "paired_samsung_name_hint": has_name_hint,
            },
        }

    def _provider_android(self) -> dict[str, Any]:
        devices = self._load_devices()
        android_count = sum(1 for d in devices if str(d.get("platform", "")).strip().lower() == "android")
        return {
            "name": "android",
            "ready": android_count > 0,
            "signals": {"paired_android_devices": android_count},
        }

    def _provider_ubuntu(self) -> dict[str, Any]:
        os_release = Path("/etc/os-release")
        name = ""
        if os_release.exists():
            for line in os_release.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("ID="):
                    name = line.split("=", 1)[1].strip().strip('"').lower()
                    break
        is_ubuntu = name == "ubuntu"
        return {"name": "ubuntu", "ready": is_ubuntu, "signals": {"os_id": name or "unknown", "is_ubuntu": is_ubuntu}}

    def run_once(self) -> dict[str, Any]:
        providers = [
            self._provider_github(),
            self._provider_google(),
            self._provider_microsoft(),
            self._provider_openai(),
            self._provider_claude_sonnet(),
            self._provider_grok_xai(),
            self._provider_shinkai(),
            self._provider_ollama(),
            self._provider_nvidia(),
            self._provider_intel(),
            self._provider_amd(),
            self._provider_razer(),
            self._provider_samsung_android(),
            self._provider_android(),
            self._provider_ubuntu(),
        ]
        ready = sum(1 for p in providers if p.get("ready"))
        payload = {
            "ts_utc": utc_now(),
            "providers_total": len(providers),
            "providers_ready": ready,
            "providers_not_ready": len(providers) - ready,
            "providers": providers,
            "signals": {"status": "ok" if ready == len(providers) else "degraded"},
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        ev = {"ts_utc": payload["ts_utc"], "event": "external_provider_mesh_cycle", "ready": ready, "total": len(providers)}
        self._append_jsonl(self.events_file, ev)
        self._append_jsonl(self.audit_stream_file, {"ts_utc": payload["ts_utc"], "source": "external_provider_mesh", "payload": payload})
        return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="External provider sync mesh status for ecosystem gateways.")
    p.add_argument("--once", action="store_true")
    p.add_argument("--interval-sec", type=int, default=30)
    return p


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = ExternalProviderMesh(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        out = svc.run_once()
        print(json.dumps({"ts_utc": out.get("ts_utc"), "ready": out.get("providers_ready"), "total": out.get("providers_total")}, ensure_ascii=True))
        time.sleep(max(5, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
