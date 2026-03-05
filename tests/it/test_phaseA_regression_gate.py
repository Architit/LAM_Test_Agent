from __future__ import annotations

from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_ROOT = REPO_ROOT.parent

RADRILONIUMA_PROJECT = WORK_ROOT / "RADRILONIUMA-PROJECT"
ARCHIVATOR_AGENT = WORK_ROOT / "Archivator_Agent"
OPERATOR_AGENT = WORK_ROOT / "Operator_Agent"


@pytest.mark.integration
def test_phaseA_task_spec_v11_markers_present() -> None:
    template = RADRILONIUMA_PROJECT / "devkit" / "task_spec_template.yaml"
    assert template.exists(), f"missing canonical template: {template}"
    text = template.read_text(encoding="utf-8")

    required_tokens = [
        "spec_version",
        "task_id",
        "goal",
        "derivation_only",
        "patch_sha256",
        "timeout_ms",
        "max_output_tokens",
    ]
    for token in required_tokens:
        assert token in text, f"missing task-spec v1.1 marker: {token}"


@pytest.mark.integration
def test_phaseA_archivator_integrity_chain_markers_present() -> None:
    patch_helper = ARCHIVATOR_AGENT / "devkit" / "patch.sh"
    assert patch_helper.exists(), f"missing patch helper: {patch_helper}"
    text = patch_helper.read_text(encoding="utf-8")

    for token in ("--sha256", "missing_patch_sha256", "integrity_mismatch", "artifact_hash", "spec_hash", "apply_result="):
        assert token in text, f"missing integrity marker: {token}"


@pytest.mark.integration
def test_phaseA_operator_fail_fast_contract_markers_present() -> None:
    queue_manager = OPERATOR_AGENT / "agent" / "queue_manager.py"
    assert queue_manager.exists(), f"missing operator envelope source: {queue_manager}"
    text = queue_manager.read_text(encoding="utf-8")

    assert "validate_task_spec_envelope" in text
    assert "verify_patch_integrity" in text
    assert "constraints.derivation_only must be true" in text

    # Keep marker-based checks resilient to literal formatting.
    assert re.search(r"ERROR_CODE_[A-Z_]*INTEGRITY_MISMATCH", text), "missing integrity mismatch error code constant"
    assert re.search(r"ERROR_CODE_[A-Z_]*PRECONDITION_FAILED", text), "missing precondition fail-fast error code constant"
