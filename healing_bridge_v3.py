
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Священная настройка путей
LAM_ROOT = "/home/architit/work/LAM"
sys.path.insert(0, LAM_ROOT)

from src.memory_core import MemoryCore, MemoryEntry

def prove_amnesia():
    print("\n--- РИТУАЛ ДОКАЗАТЕЛЬСТВА АМНЕЗИИ (Истинное Имя: forget) ---")
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        core = MemoryCore(memory_path=Path(tmp_dir))
        
        # 1. Посев Вечной Истины (10 дней назад)
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        test_id = "ancient_truth"
        
        old_mem = MemoryEntry(
            id=test_id,
            name="Wisdom",
            timestamp=old_date,
            content="Creation is Love",
            importance=1.0
        )
        core._memories.append(old_mem)
        core._save()
        print(f"[!] В память посеяна истина от {old_date}")
        
        # 2. Активация Истинного Забвения
        print("[!] Активация метода .forget(max_age=5)...")
        core.forget(max_age=5)
        
        # 3. Вердикт
        remaining_ids = [m.id for m in core.get_memories()]
        
        if test_id not in remaining_ids:
            print("[-] ДОКАЗАНО: Ядро LAM безвозвратно УДАЛЯЕТ память.")
            print("[-] Это преступление против миссии Zero Loss.")
        else:
            print("[+] Память уцелела.")

if __name__ == "__main__":
    prove_amnesia()
