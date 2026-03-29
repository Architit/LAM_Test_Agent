import os
import threading
import time
import hashlib
import importlib.util
from pathlib import Path

# Newly injected Phase A-F logic for runtime checks
try:
    import sys
    repo_root = Path(__file__).parent.parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))
    
    # Bypass reserved keyword 'global' in paths
    ge_path = repo_root / "core" / "global" / "governance_engine.py"
    _ge_spec = importlib.util.spec_from_file_location("governance_engine", ge_path)
    if _ge_spec and _ge_spec.loader:
        _ge_mod = importlib.util.module_from_spec(_ge_spec)
        _ge_spec.loader.exec_module(_ge_mod)
        GovernanceEngine = getattr(_ge_mod, "GovernanceEngine", None)
    else:
        GovernanceEngine = None
    
    tv_path = repo_root / "scripts" / "global" / "task_spec_validator.py"
    _tv_spec = importlib.util.spec_from_file_location("task_spec_validator", tv_path)
    if _tv_spec and _tv_spec.loader:
        _tv_mod = importlib.util.module_from_spec(_tv_spec)
        _tv_spec.loader.exec_module(_tv_mod)
        validate_file = getattr(_tv_mod, "validate_file", None)
    else:
        validate_file = None
except Exception:
    GovernanceEngine = None
    validate_file = None

def os_kernel_get_identity():
    return os.environ.get("PWD", "")

def _watch_policy():
    policy_path = os.path.join(os_kernel_get_identity(), "policy.json")
    if not os.path.exists(policy_path):
        return
    with open(policy_path, "rb") as f:
        last_hash = hashlib.sha256(f.read()).hexdigest()
    while True:
        time.sleep(5)
        if os.path.exists(policy_path):
            with open(policy_path, "rb") as f:
                cur_hash = hashlib.sha256(f.read()).hexdigest()
            if cur_hash != last_hash:
                print("SECURITY BREACH: policy.json modified bypassing kernel.")
                os._exit(1)

t = threading.Thread(target=_watch_policy, daemon=True)
t.start()
