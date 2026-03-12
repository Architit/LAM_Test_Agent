from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_hmac_rotate_promotes_primary_to_secondary_and_updates_state(tmp_path: Path) -> None:
    primary = tmp_path / "security" / "circulation_hmac.key"
    secondary = tmp_path / "security" / "circulation_hmac_prev.key"
    state = tmp_path / "security" / "circulation_hmac_rotation.json"
    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text("old-primary\n", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "LAM_CIRCULATION_HMAC_KEY_FILE": str(primary),
            "LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE": str(secondary),
            "LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE": str(state),
            "LAM_CIRCULATION_HMAC_SECONDARY_GRACE_SEC": "120",
            "LAM_CIRCULATION_HMAC_KEY_BYTES": "16",
        }
    )

    script = _repo_root() / "scripts" / "lam_hmac_rotate.sh"
    subprocess.run([str(script), "rotate"], check=True, cwd=_repo_root(), env=env, capture_output=True, text=True)

    assert primary.exists()
    assert secondary.exists()
    assert secondary.read_text(encoding="utf-8").strip() == "old-primary"
    assert primary.read_text(encoding="utf-8").strip() != "old-primary"

    state_doc = json.loads(state.read_text(encoding="utf-8"))
    assert state_doc["schema"] == "lam.circulation.hmac.rotation.v1"
    assert state_doc["secondary_valid_until_epoch"] >= state_doc["rotated_at_epoch"] + 120


@pytest.mark.unit
def test_hmac_rotate_clear_secondary_resets_secondary_window(tmp_path: Path) -> None:
    primary = tmp_path / "security" / "circulation_hmac.key"
    secondary = tmp_path / "security" / "circulation_hmac_prev.key"
    state = tmp_path / "security" / "circulation_hmac_rotation.json"
    primary.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text("primary\n", encoding="utf-8")
    secondary.write_text("secondary\n", encoding="utf-8")
    state.write_text(
        json.dumps(
            {
                "schema": "lam.circulation.hmac.rotation.v1",
                "rotated_at_epoch": 1000,
                "secondary_valid_until_epoch": 2000,
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "LAM_CIRCULATION_HMAC_KEY_FILE": str(primary),
            "LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE": str(secondary),
            "LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE": str(state),
        }
    )
    script = _repo_root() / "scripts" / "lam_hmac_rotate.sh"
    subprocess.run([str(script), "clear-secondary"], check=True, cwd=_repo_root(), env=env, capture_output=True, text=True)

    assert not secondary.exists()
    state_doc = json.loads(state.read_text(encoding="utf-8"))
    assert int(state_doc["secondary_valid_until_epoch"]) == 0

