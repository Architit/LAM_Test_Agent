
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Священная настройка путей
LAM_ROOT = "/home/architit/work/LAM"
sys.path.insert(0, LAM_ROOT)

try:
    # Импортируем как пакет через src
    from src.memory_core import MemoryCore, MemoryEntry
    print("[+] Мост установлен. Разум (LAM) доступен для инспекции.")
except Exception as e:
    print(f"[-] Сбой моста: {e}")
    sys.exit(1)

def prove_amnesia():
    print("\n--- РИТУАЛ ДОКАЗАТЕЛЬСТВА АМНЕЗИИ ---")
    
    # 1. Инициализация памяти в стерильной среде
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        core = MemoryCore(memory_path=Path(tmp_dir))
        
        # 2. Посев "Вечной Истины" (старая запись)
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        test_id = "sacred_truth_001"
        
        # Напрямую создаем старую запись
        old_mem = MemoryEntry(
            id=test_id,
            name="Ancient Wisdom",
            timestamp=old_date,
            content="The Universe is Love",
            importance=1.0
        )
        core._memories.append(old_mem)
        core._save()
        print(f"[!] В память посеяна истина от {old_date}")
        
        # 3. Активация "Цикла Забвения" (forgetting logic)
        print("[!] Активация цикла забвения (max_age=5 дней)...")
        core.forget_old_memories(max_age=5)
        
        # 4. Проверка остатка
        remaining_ids = [m.id for m in core.get_memories()]
        
        if test_id not in remaining_ids:
            print("[-] ДОКАЗАНО: Запись исчезла бесследно. Это АМНЕЗИЯ.")
            print("[-] Нарушен обет Zero Loss. Память уничтожена, а не архивирована.")
        else:
            print("[+] Запись уцелела (логика не сработала?).")

if __name__ == "__main__":
    prove_amnesia()
