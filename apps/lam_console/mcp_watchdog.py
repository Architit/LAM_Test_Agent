#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MCPWatchdog:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.state_file = self.hub_root / "mcp_watchdog_state.json"
        self.events_file = self.bridge_root / "events.jsonl"
        self.auto_heal = os.getenv("LAM_MCP_AUTO_HEAL", "1") not in {"0", "false", "False"}
        self.cooldown_sec = int(os.getenv("LAM_MCP_HEAL_COOLDOWN_SEC", "300"))
        self.last_heal_epoch = 0.0

    @staticmethod
    def _run(cmd: list[str], timeout_sec: int = 30) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_sec, check=False)
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except Exception as exc:  # pragma: no cover - protective guard
            return 99, "", str(exc)

    def _append_event(self, payload: dict[str, Any]) -> None:
        with self.events_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _transport_check(self) -> dict[str, Any]:
        ext_dir = Path.home() / ".gemini" / "extensions" / "google-workspace"
        index_js = ext_dir / "dist" / "index.js"
        if not index_js.exists():
            return {"ok": False, "reason": "extension_dist_missing"}
        if shutil.which("node") is None:
            return {"ok": False, "reason": "node_missing"}
        payload = (
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"lam-mcp-watchdog","version":"1.0"}}}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n'
        )
        try:
            proc = subprocess.run(
                ["node", str(index_js), "--use-dot-names"],
                input=payload,
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = '"id":1' in out and '"id":2' in out
            return {
                "ok": ok,
                "rc": proc.returncode,
                "reason": "ok" if ok else "initialize_or_tools_list_failed",
            }
        except Exception as exc:  # pragma: no cover
            return {"ok": False, "reason": str(exc)}

    def check_health(self) -> dict[str, Any]:
        gemini_bin = shutil.which("gemini")
        status: dict[str, Any] = {
            "ts_utc": utc_now(),
            "gemini_installed": bool(gemini_bin),
            "gemini_bin": gemini_bin or "",
            "google_workspace_registered": False,
            "transport_ok": False,
            "overall_ok": False,
        }
        if not gemini_bin:
            return status

        rc, out, err = self._run(["gemini", "mcp", "list"], timeout_sec=20)
        merged = f"{out}\n{err}".lower()
        status["mcp_list_rc"] = rc
        status["google_workspace_registered"] = "google-workspace" in merged

        transport = self._transport_check()
        status["transport_ok"] = bool(transport.get("ok"))
        status["transport"] = transport

        status["overall_ok"] = bool(status["google_workspace_registered"] and status["transport_ok"])
        return status

    def heal(self) -> dict[str, Any]:
        ext_url = os.getenv("LAM_GWS_EXTENSION_URL", "https://github.com/googleworkspace/cli")
        fallback_url = os.getenv("LAM_GWS_EXTENSION_FALLBACK_URL", "https://github.com/gemini-cli-extensions/workspace")
        steps: list[dict[str, Any]] = []

        for cmd in (["gemini", "auth", "clear"], ["gemini", "extensions", "uninstall", "google-workspace"]):
            rc, out, err = self._run(cmd, timeout_sec=30)
            steps.append({"cmd": cmd, "rc": rc, "stdout": out, "stderr": err})

        rc, out, err = self._run(["gemini", "extensions", "install", ext_url], timeout_sec=60)
        steps.append({"cmd": ["gemini", "extensions", "install", ext_url], "rc": rc, "stdout": out, "stderr": err})

        if rc != 0 and fallback_url and fallback_url != ext_url:
            frc, fout, ferr = self._run(["gemini", "extensions", "install", fallback_url], timeout_sec=60)
            steps.append(
                {
                    "cmd": ["gemini", "extensions", "install", fallback_url],
                    "rc": frc,
                    "stdout": fout,
                    "stderr": ferr,
                }
            )

        post = self.check_health()
        result = {"ts_utc": utc_now(), "action": "heal", "steps": steps, "post_health": post, "ok": bool(post.get("overall_ok"))}
        return result

    def run_once(self, force_heal: bool = False) -> dict[str, Any]:
        health = self.check_health()
        result: dict[str, Any] = {"ts_utc": utc_now(), "health": health, "heal_attempted": False, "heal": {}}

        should_heal = force_heal or (self.auto_heal and not bool(health.get("overall_ok")))
        now = time.time()
        if should_heal and (force_heal or now - self.last_heal_epoch >= self.cooldown_sec):
            result["heal_attempted"] = True
            result["heal"] = self.heal()
            self.last_heal_epoch = now
        elif should_heal:
            result["heal_skipped"] = "cooldown"

        self.state_file.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._append_event({"ts_utc": utc_now(), "event": "mcp_watchdog", "ok": bool(result.get("health", {}).get("overall_ok")), "heal_attempted": result.get("heal_attempted", False)})
        return result



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM MCP watchdog with auto-heal for google-workspace MCP.")
    parser.add_argument("--once", action="store_true", help="Run one check cycle and exit.")
    parser.add_argument("--interval-sec", type=int, default=90, help="Loop interval for daemon mode.")
    parser.add_argument("--heal-now", action="store_true", help="Force immediate heal sequence.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    watchdog = MCPWatchdog(repo_root)

    if args.once:
        print(json.dumps(watchdog.run_once(force_heal=args.heal_now), ensure_ascii=True))
        return 0

    while True:
        payload = watchdog.run_once(force_heal=args.heal_now)
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "ok": payload.get("health", {}).get("overall_ok"), "heal_attempted": payload.get("heal_attempted")}, ensure_ascii=True))
        time.sleep(max(5, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
