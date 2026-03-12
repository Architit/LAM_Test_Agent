from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import time
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_once(env: dict[str, str]) -> None:
    script = _repo_root() / "scripts" / "lam_realtime_circulation.sh"
    subprocess.run([str(script), "--once"], check=True, cwd=_repo_root(), env=env, capture_output=True, text=True)


def _sign_payload(payload_bytes: bytes, key: str) -> dict[str, str]:
    sha = hashlib.sha256(payload_bytes).hexdigest()
    sig = hmac.new(key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return {"sha256": sha, "hmac_sha256": sig}


def _write_remote_report(state_root: Path, producer: str, report_name: str, key: str) -> Path:
    report_dir = state_root / "inversion" / "outbox" / producer
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / report_name
    payload = {
        "schema": "lam.inversion.test_reports.v1",
        "generated_utc": "2026-03-07T00:00:00Z",
        "producer_node": producer,
        "summaries": [{"name": "stub"}],
        "background_errors_tail": [],
    }
    report.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    sig = _sign_payload(report.read_bytes(), key)
    sig_doc = {
        "schema": "lam.inversion.sig.v1",
        "ts_utc": "2026-03-07T00:00:00Z",
        "key_id": "test",
        "sha256": sig["sha256"],
        "hmac_sha256": sig["hmac_sha256"],
    }
    (report_dir / f"{report_name}.sig.json").write_text(
        json.dumps(sig_doc, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _read_index_events(state_root: Path) -> list[dict]:
    index_file = state_root / "inversion" / "index.jsonl"
    if not index_file.exists():
        return []
    events = []
    for line in index_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


@pytest.mark.integration
def test_realtime_circulation_accepts_valid_signature(tmp_path: Path) -> None:
    state_root = tmp_path / "circulation"
    local_node = "local-node"
    producer = "peer-a"
    report_name = "report_peer_a.json"
    key = "primary-secret"
    _write_remote_report(state_root, producer, report_name, key)

    env = os.environ.copy()
    env.update(
        {
            "LAM_CIRCULATION_STATE_ROOT": str(state_root),
            "LAM_NODE_ID": local_node,
            "LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR": "1",
            "LAM_CIRCULATION_HMAC_KEY": key,
        }
    )
    _run_once(env)

    ingested = state_root / "inversion" / "inbox" / producer / report_name
    assert ingested.exists()
    events = _read_index_events(state_root)
    assert any(e.get("event") == "inversion_report_ingested" and e.get("producer") == producer for e in events)


@pytest.mark.integration
def test_realtime_circulation_rejects_invalid_signature(tmp_path: Path) -> None:
    state_root = tmp_path / "circulation"
    local_node = "local-node"
    producer = "peer-b"
    report_name = "report_peer_b.json"
    _write_remote_report(state_root, producer, report_name, "wrong-secret")

    env = os.environ.copy()
    env.update(
        {
            "LAM_CIRCULATION_STATE_ROOT": str(state_root),
            "LAM_NODE_ID": local_node,
            "LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR": "1",
            "LAM_CIRCULATION_HMAC_KEY": "primary-secret",
        }
    )
    _run_once(env)

    ingested = state_root / "inversion" / "inbox" / producer / report_name
    assert not ingested.exists()
    events = _read_index_events(state_root)
    assert any(e.get("event") == "inversion_report_rejected_crypto" and e.get("producer") == producer for e in events)


@pytest.mark.integration
def test_realtime_circulation_accepts_secondary_key_within_grace(tmp_path: Path) -> None:
    state_root = tmp_path / "circulation"
    local_node = "local-node"
    producer = "peer-c"
    report_name = "report_peer_c.json"
    secondary_key = "secondary-secret"
    _write_remote_report(state_root, producer, report_name, secondary_key)

    env = os.environ.copy()
    env.update(
        {
            "LAM_CIRCULATION_STATE_ROOT": str(state_root),
            "LAM_NODE_ID": local_node,
            "LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR": "1",
            "LAM_CIRCULATION_HMAC_KEY": "new-primary-secret",
            "LAM_CIRCULATION_HMAC_SECONDARY_KEY": secondary_key,
            "LAM_CIRCULATION_HMAC_SECONDARY_VALID_UNTIL_EPOCH": str(int(time.time()) + 600),
        }
    )
    _run_once(env)

    ingested = state_root / "inversion" / "inbox" / producer / report_name
    assert ingested.exists()


@pytest.mark.integration
def test_realtime_circulation_rejects_secondary_key_after_grace(tmp_path: Path) -> None:
    state_root = tmp_path / "circulation"
    local_node = "local-node"
    producer = "peer-d"
    report_name = "report_peer_d.json"
    secondary_key = "secondary-secret"
    _write_remote_report(state_root, producer, report_name, secondary_key)

    env = os.environ.copy()
    env.update(
        {
            "LAM_CIRCULATION_STATE_ROOT": str(state_root),
            "LAM_NODE_ID": local_node,
            "LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR": "1",
            "LAM_CIRCULATION_HMAC_KEY": "new-primary-secret",
            "LAM_CIRCULATION_HMAC_SECONDARY_KEY": secondary_key,
            "LAM_CIRCULATION_HMAC_SECONDARY_VALID_UNTIL_EPOCH": str(int(time.time()) - 10),
        }
    )
    _run_once(env)

    ingested = state_root / "inversion" / "inbox" / producer / report_name
    assert not ingested.exists()
    events = _read_index_events(state_root)
    assert any(
        e.get("event") == "inversion_report_rejected_crypto"
        and e.get("producer") == producer
        and int(e.get("rc", 0)) == 6
        for e in events
    )

