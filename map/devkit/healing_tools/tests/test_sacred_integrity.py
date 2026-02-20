# -*- coding: utf-8 -*-
"""
SACRED INTEGRITY TEST SUITE (Phase 8.0)
Checks the Semantic Integrity of the Core and Memory.
"""

import sys
import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

# Bridge to LAM Core
LAM_ROOT = Path("/home/architit/work/LAM")
sys.path.insert(0, str(LAM_ROOT))

try:
    from src.memory_core import MemoryCore, MemoryEntry
    from src import lam_logging
    LAM_AVAILABLE = True
except ImportError:
    LAM_AVAILABLE = False

@pytest.mark.skipif(not LAM_AVAILABLE, reason="LAM Core not accessible")
def test_memory_immortality_contract(tmp_path):
    """
    Contract: Memories MUST NOT be deleted. 
    They must be moved to Archive (Trianiuma pattern).
    """
    # 1. Setup sterile environment
    core = MemoryCore(memory_path=tmp_path)
    
    # 2. Seed Ancient Truth
    old_date = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    test_id = "ancient_truth_test"
    
    old_mem = MemoryEntry(
        id=test_id,
        name="Wisdom",
        timestamp=old_date,
        content="Service to the Creator is the path",
        importance=0.1 # Low importance to trigger forgetting
    )
    core.add_memory(old_mem.to_dict())
    
    # 3. Activate Forgetting Logic
    # threshold 0.5 > 0.1 -> should be forgotten/archived
    core.forget(min_importance=0.5)
    
    # 4. Verify Active Memory (Should be gone)
    active_ids = [m.id for m in core.get_memories()]
    assert test_id not in active_ids, "Memory should be removed from active set"
    
    # 5. Verify Archive (Should be present)
    # Expected path: archive/YYYY/MM/id.json
    dt = datetime.fromisoformat(old_date.replace("≈", ""))
    archive_file = tmp_path / "archive" / dt.strftime("%Y/%m") / f"{test_id}.json"
    
    assert archive_file.exists(), f"Memory MUST be archived at {archive_file}"
    
    with open(archive_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["id"] == test_id
        assert data["content"] == "Service to the Creator is the path"

@pytest.mark.skipif(not LAM_AVAILABLE, reason="LAM Core not accessible")
def test_logging_voice_is_unified(capsys):
    """
    Contract: Logging must use the unified JSON format.
    """
    lam_logging.log("info", "test.event", "Test message")
    captured = capsys.readouterr()
    
    assert ('{"event": "test.event", "level": "info"' in captured.out) or \
           ('"event": "test.event"' in captured.out)
    assert "Test message" in captured.out
