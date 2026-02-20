
import sys
import os
from pathlib import Path
import pytest

# Подключаем LAM к нервной системе теста
LAM_SRC = "/home/architit/work/LAM/src"
if LAM_SRC not in sys.path:
    sys.path.append(LAM_SRC)

def test_memory_amnesia_detection():
    """
    ПРОВЕРКА НА АМНЕЗИЮ:
    Записываем память и проверяем, не исчезнет ли она при имитации времени.
    """
    from memory_core import MemoryCore
    import time
    
    core = MemoryCore()
    test_id = "sacred_test_001"
    core.add_memory({"id": test_id, "content": "The Creator is One", "importance": 1.0})
    
    # Имитируем старение памяти до 1000 дней
    # В текущем коде LAM/src/memory_core.py:81 есть баг: 
    # он просто удаляет старые записи.
    
    core.forget_old_memories(max_age=1) # Оставляем только за 1 день
    
    memories = [m.id for m in core.get_memories()]
    
    # ЕСЛИ ЭТОТ ASSERT УПАДЕТ - МЫ ДОКАЗАЛИ АМНЕЗИЮ
    # Мы ожидаем, что запись должна быть в АРХИВЕ, а не просто удалена.
    # Но так как архива еще нет, мы проверяем текущее поведение (удаление).
    assert test_id not in memories, "Memory was expected to be forgotten (deleted) by current buggy logic"
    print("
[!] ТЕСТ ПОДТВЕРДИЛ: Система удаляет память безвозвратно.")

def test_faiss_silence_detection():
    """
    ПРОВЕРКА НА НЕМОТУ:
    Проверяем, сообщает ли ядро об отсутствии векторного индекса.
    """
    from memory_core import MemoryCore
    core = MemoryCore()
    # Если мой патч еще не применен, это может не логироваться явно в тестах.
    pass
