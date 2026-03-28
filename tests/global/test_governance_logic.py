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

def test_governance_pressure(tmp_path):
    engine = GovernanceEngine(tmp_path)
    
    # Define virtual domains
    domains = {
        'legal': [tmp_path / 'IDENTITY.md'],
        'execution': [tmp_path / 'ROADMAP.md']
    }
    
    # 1. Test degraded state (no files exist)
    report = engine.evaluate_health(domains)
    assert report['pressure'] == 1.0
    assert report['status'] == 'STABILIZING'
    
    # 2. Test awakened state
    (tmp_path / 'IDENTITY.md').touch()
    (tmp_path / 'ROADMAP.md').touch()
    report = engine.evaluate_health(domains)
    assert report['pressure'] == 0.0
    assert report['status'] == 'AWAKENED'
