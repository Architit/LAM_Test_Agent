import pytest
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "core" / "global" / "governance_engine.py"

_SPEC = importlib.util.spec_from_file_location("governance_engine", MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MODULE)
GovernanceEngine = MODULE.GovernanceEngine

def test_full_governance_awakening(tmp_path):
    engine = GovernanceEngine(tmp_path)
    
    # 1. Test Intent & Safety (Phase E & F)
    safe_intent = {
        'op': 'ISSUE_DIRECTIVE',
        'id': 'DIR_001',
        'payload': {'action': 'sync'},
        'current_pressure': 0.2
    }
    unsafe_intent = {
        'op': 'ISSUE_DIRECTIVE',
        'id': 'DIR_002',
        'payload': {'action': 'sync'},
        'current_pressure': 0.9
    }
    
    assert 'broadcasted' in engine.process_intent(safe_intent)
    assert engine.process_intent(unsafe_intent) == 'blocked_by_pressure_safety'
    
    # 2. Test Transport (Phase D)
    directive_file = tmp_path / '.gateway' / 'hub' / 'directives' / 'DIR_001.json'
    assert directive_file.exists()
    
    # 3. Test Memory (Phase C)
    engine.save_snapshot('ACTIVE', 0.2) # Explicitly trigger state save
    assert (tmp_path / 'WORKFLOW_SNAPSHOT_STATE.json').exists()
