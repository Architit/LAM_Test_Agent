from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_safety_stack import load_stack, validate_stack


ROOT = Path(__file__).resolve().parents[2]
STACK_PATH = ROOT / "memory" / "FRONT" / "ECOSYSTEM_SAFETY_RESOURCE_STACK_V1.json"


@pytest.mark.unit
def test_validate_stack_ok_on_current_stack() -> None:
    stack = load_stack(STACK_PATH)
    assert validate_stack(stack) == []


@pytest.mark.unit
def test_validate_stack_rejects_duplicate_ids(tmp_path: Path) -> None:
    data = {
        "layers": [
            {"id": "x", "order": 1, "domain": "protocol", "required": True},
            {"id": "x", "order": 2, "domain": "ci", "required": True},
        ]
    }
    path = tmp_path / "stack.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    stack = load_stack(path)
    errors = validate_stack(stack)
    assert any("layer ids must be unique" in e for e in errors)


@pytest.mark.unit
def test_validate_stack_rejects_non_contiguous_order(tmp_path: Path) -> None:
    data = {
        "layers": [
            {"id": "a", "order": 1, "domain": "protocol", "required": True},
            {"id": "b", "order": 3, "domain": "ci", "required": True},
        ]
    }
    path = tmp_path / "stack.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    stack = load_stack(path)
    errors = validate_stack(stack)
    assert any("contiguous" in e for e in errors)
