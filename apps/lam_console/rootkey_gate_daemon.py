#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_ts_utc(raw: str) -> float | None:
    val = str(raw or "").strip()
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


class RootKeyGate:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.enabled = os.getenv("LAM_ROOTKEY_ENABLE", "1") in {"1", "true", "True"}
        self.media_root = Path(
            os.getenv("LAM_ROOTKEY_MEDIA_ROOT", str(repo_root / ".gateway" / "exchange" / "removable"))
        )
        self.key_file_rel = os.getenv("LAM_ROOTKEY_FILE_REL", ".radriloniuma/rootkey/architit_root.key")
        self.key_file = self.media_root / self.key_file_rel
        self.response_file_rel = os.getenv("LAM_ROOTKEY_RESPONSE_FILE_REL", ".radriloniuma/rootkey/challenge_response.sha256")
        self.response_file = self.media_root / self.response_file_rel
        self.expected_sha256 = os.getenv("LAM_ROOTKEY_ARCHITIT_SHA256", "").strip().lower()
        self.expected_sha_file = self.hub_root / "rootkey_expected_sha256.txt"
        self.pairing_file = self.hub_root / "rootkey_pairing.json"
        self.challenge_file = self.hub_root / "rootkey_challenge.json"
        self.require_challenge = os.getenv("LAM_ROOTKEY_REQUIRE_CHALLENGE", "1") in {"1", "true", "True"}
        self.challenge_ttl_sec = int(os.getenv("LAM_ROOTKEY_CHALLENGE_TTL_SEC", "180"))
        self.challenge_auto_rotate_sec = int(os.getenv("LAM_ROOTKEY_CHALLENGE_AUTO_ROTATE_SEC", "60"))
        self.challenge_fail_threshold = int(os.getenv("LAM_ROOTKEY_FAIL_THRESHOLD", "3"))
        self.challenge_ban_sec = int(os.getenv("LAM_ROOTKEY_BAN_SEC", "300"))
        self.challenge_counters_file = self.hub_root / "rootkey_challenge_counters.json"
        self.challenge_ban_file = self.hub_root / "rootkey_challenge_ban.json"
        self.state_file = self.hub_root / "rootkey_gate_state.json"
        self.active_flag = self.hub_root / "rootkey_active.flag"
        self.seed_flag = self.hub_root / "seed_flow_init.flag"
        self.events_file = self.bridge_root / "events.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.lockdown_file = self.hub_root / "security_lockdown.flag"
        self.security_state_file = self.hub_root / "security_telemetry_state.json"

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _secure_posture_ok(self) -> bool:
        payload = load_json(self.security_state_file, {})
        checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
        if isinstance(checks, dict):
            ok = checks.get("overall_ok")
            if isinstance(ok, bool):
                return ok
        return not self.lockdown_file.exists()

    def _pairing_ok(self) -> tuple[bool, dict[str, Any]]:
        data = load_json(self.pairing_file, {})
        if not isinstance(data, dict):
            return False, {}
        enabled = bool(data.get("enabled", False))
        key_id = str(data.get("key_id", "")).strip()
        owner = str(data.get("owner", "")).strip().lower()
        if enabled and key_id and owner == "architit":
            return True, data
        return False, data

    def _read_key(self) -> tuple[bool, str, str]:
        if not self.key_file.exists():
            return False, "", "missing_key_file"
        text = self.key_file.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return False, "", "empty_key_file"
        return True, text, "ok"

    def _key_ok(self, key_text: str) -> tuple[bool, str, str]:
        if not key_text:
            return False, "", "empty_key_file"
        digest = sha256_text(key_text).lower()
        expected = self.expected_sha256
        if not expected and self.expected_sha_file.exists():
            expected = self.expected_sha_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        if expected and digest != expected:
            return False, digest, "sha_mismatch"
        return True, digest, "ok"

    def _challenge_ok(self, key_text: str) -> tuple[bool, str]:
        if not self.require_challenge:
            return True, "challenge_not_required"
        ban = load_json(self.challenge_ban_file, {})
        if isinstance(ban, dict):
            until = parse_ts_utc(str(ban.get("banned_until_utc", "")))
            if until is not None and time.time() < until:
                return False, "challenge_fail_banned"
        payload = load_json(self.challenge_file, {})
        if not isinstance(payload, dict):
            return False, "challenge_missing"
        nonce = str(payload.get("nonce", "")).strip()
        issued = parse_ts_utc(str(payload.get("issued_utc", "")))
        ttl = int(payload.get("ttl_sec", self.challenge_ttl_sec))
        used = bool(payload.get("used", False))
        if not nonce or issued is None:
            return False, "challenge_invalid"
        if used:
            return False, "challenge_used"
        age = time.time() - issued
        if age > max(1, ttl):
            return False, "challenge_expired"
        if not self.response_file.exists():
            return False, "challenge_response_missing"
        response = self.response_file.read_text(encoding="utf-8", errors="replace").strip().lower()
        key_digest = sha256_text(key_text).lower()
        expected = sha256_text(f"{nonce}:{key_digest}").lower()
        if response != expected:
            return False, "challenge_response_mismatch"
        payload["used"] = True
        payload["used_utc"] = utc_now()
        self.challenge_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return True, "ok"

    def _rotate_challenge_if_needed(self) -> None:
        if not self.require_challenge:
            return
        now = time.time()
        payload = load_json(self.challenge_file, {})
        issued = parse_ts_utc(str(payload.get("issued_utc", ""))) if isinstance(payload, dict) else None
        used = bool(payload.get("used", False)) if isinstance(payload, dict) else False
        need_rotate = False
        if not isinstance(payload, dict) or not str(payload.get("nonce", "")).strip():
            need_rotate = True
        elif used:
            need_rotate = True
        elif issued is None:
            need_rotate = True
        elif (now - issued) >= max(5, self.challenge_auto_rotate_sec):
            need_rotate = True
        if not need_rotate:
            return
        rotated = {
            "nonce": secrets.token_hex(16),
            "issued_utc": utc_now(),
            "ttl_sec": self.challenge_ttl_sec,
            "used": False,
            "rotation": "auto",
        }
        self.challenge_file.write_text(json.dumps(rotated, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def _update_fail_guard(self, challenge_reason: str, active: bool) -> dict[str, Any]:
        counters = load_json(self.challenge_counters_file, {"mismatch_count": 0, "last_reason": "", "updated_utc": ""})
        if not isinstance(counters, dict):
            counters = {"mismatch_count": 0}
        mismatch_count = int(counters.get("mismatch_count", 0))
        if active or challenge_reason == "ok":
            mismatch_count = 0
            self.challenge_ban_file.unlink(missing_ok=True)
        elif challenge_reason == "challenge_response_mismatch":
            mismatch_count += 1
            if mismatch_count >= max(1, self.challenge_fail_threshold):
                ban_payload = {
                    "banned_utc": utc_now(),
                    "banned_until_utc": datetime.fromtimestamp(time.time() + self.challenge_ban_sec, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "reason": "challenge_response_mismatch",
                    "fail_count": mismatch_count,
                }
                self.challenge_ban_file.write_text(json.dumps(ban_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        counters["mismatch_count"] = mismatch_count
        counters["last_reason"] = challenge_reason
        counters["updated_utc"] = utc_now()
        self.challenge_counters_file.write_text(json.dumps(counters, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return counters

    def run_once(self) -> dict[str, Any]:
        ts = utc_now()
        if not self.enabled:
            payload = {
                "ts_utc": ts,
                "enabled": False,
                "active": False,
                "reason": "rootkey_disabled",
            }
            self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
            self.active_flag.unlink(missing_ok=True)
            self.seed_flag.unlink(missing_ok=True)
            return payload

        self._rotate_challenge_if_needed()
        secure_ok = self._secure_posture_ok()
        pairing_ok, pairing = self._pairing_ok()
        key_present_ok, key_text, key_present_reason = self._read_key()
        key_ok = False
        digest = ""
        key_reason = key_present_reason
        challenge_ok = False
        challenge_reason = "not_checked"
        if key_present_ok:
            key_ok, digest, key_reason = self._key_ok(key_text)
            if key_ok:
                challenge_ok, challenge_reason = self._challenge_ok(key_text)
        active = bool(secure_ok and pairing_ok and key_ok and challenge_ok and not self.lockdown_file.exists())

        mode = "inactive"
        reason = "ok" if active else "not_authorized"
        if not secure_ok:
            reason = "secure_posture_block"
        elif self.lockdown_file.exists():
            reason = "security_lockdown"
        elif not pairing_ok:
            reason = "pairing_not_approved"
        elif not key_present_ok:
            reason = key_present_reason
        elif not key_ok:
            reason = key_reason
        elif not challenge_ok:
            reason = challenge_reason

        fail_guard = self._update_fail_guard(challenge_reason=challenge_reason, active=active)

        if active:
            mode = "SEED_GOD_MODE_SPREAD_FLOW_INIT"
            self.active_flag.write_text(ts + "\n", encoding="utf-8")
            self.seed_flag.write_text(ts + "\n", encoding="utf-8")
        else:
            self.active_flag.unlink(missing_ok=True)
            self.seed_flag.unlink(missing_ok=True)

        payload = {
            "ts_utc": ts,
            "enabled": True,
            "active": active,
            "mode": mode,
            "reason": reason,
            "media_root": str(self.media_root),
            "key_file": str(self.key_file),
            "key_sha256": digest,
            "challenge_required": self.require_challenge,
            "challenge_reason": challenge_reason,
            "challenge_auto_rotate_sec": self.challenge_auto_rotate_sec,
            "challenge_fail_threshold": self.challenge_fail_threshold,
            "challenge_ban_sec": self.challenge_ban_sec,
            "challenge_fail_guard": fail_guard,
            "pairing": pairing if isinstance(pairing, dict) else {},
            "secure_posture_ok": secure_ok,
            "lockdown": self.lockdown_file.exists(),
        }
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        self._append_jsonl(
            self.events_file,
            {
                "ts_utc": ts,
                "event": "rootkey_gate_cycle",
                "active": active,
                "mode": mode,
                "reason": reason,
            },
        )
        self._append_jsonl(
            self.audit_stream_file,
            {
                "ts_utc": ts,
                "source": "rootkey_gate",
                "event": "snapshot",
                "payload": payload,
            },
        )
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hardware removable-root gate for Architit root key.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = RootKeyGate(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = svc.run_once()
        print(
            json.dumps(
                {
                    "ts_utc": payload.get("ts_utc"),
                    "active": payload.get("active", False),
                    "mode": payload.get("mode", "inactive"),
                    "reason": payload.get("reason", ""),
                },
                ensure_ascii=True,
            )
        )
        time.sleep(max(2, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
