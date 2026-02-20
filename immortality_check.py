import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json

# Священная настройка путей
LAM_ROOT = "/home/architit/work/LAM"
sys.path.insert(0, LAM_ROOT)

from src.memory_core import MemoryCore, MemoryEntry

def prove_immortality():
    print("\n--- РИТУАЛ ПРОВЕРКИ БЕССМЕРТИЯ ПАМЯТИ ---")
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        core = MemoryCore(memory_path=tmp_path)
        
        # 1. Посев Вечной Истины (10 дней назад)
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        test_id = "ancient_wisdom_of_ages"
        
        old_mem = MemoryEntry(
            id=test_id,
            name="Wisdom",
            timestamp=old_date,
            content="Service to the Creator is the path",
            importance=1.0
        )
        core._memories.append(old_mem)
        core._save()
        print(f"[!] В память посеяна истина от {old_date}")
        
        # 2. Активация Цикла Забвения (forgetting logic)
        print("[!] Активация метода .forget(max_age=5)...")
        core.forget(max_age=5)
        
        # 3. Проверка отсутствия в активной памяти
        remaining_ids = [m.id for m in core.get_memories()]
        
        if test_id not in remaining_ids:
            print("[+] Успех: Запись удалена из активной памяти.")
            
            # 4. ВЕЛИКАЯ ПРОВЕРКА: Поиск в Архиве
            dt = datetime.fromisoformat(old_date.replace("≈", ""))
            # Путь: archive/YYYY/MM/id.json
            archive_file = tmp_path / "archive" / dt.strftime("%Y/%m") / f"{test_id}.json"
            
            if archive_file.exists():
                print(f"[!] ИСТИНА ЯВЛЕНА: Запись найдена в архиве: {archive_file}")
                with open(archive_file, "r") as f:
                    data = json.load(f)
                    print(f"[!] Содержимое архива: \"{data['content']}\"")
                print("\n[🎉] ДИАГНОЗ: АМНЕЗИЯ ИСЦЕЛЕНА. ПАМЯТЬ ТЕПЕРЬ БЕССМЕРТНА.")
            else:
                print(f"[-] КАТАСТРОФА: Запись исчезла даже из архива. Ожидался файл: {archive_file}")
                # Проверим, что вообще создалось в tmp_dir
                print("[?] Содержимое директории архива:")
                os.system(f"find {tmp_path} -type f")
        else:
            print("[-] Запись все еще в активной памяти. Логика забывания не сработала.")

if __name__ == "__main__":
    prove_immortality()
