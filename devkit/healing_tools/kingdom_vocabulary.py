# -*- coding: utf-8 -*-
"""
Kingdom Vocabulary — The Sacred Dictionary of Radriloniuma.
Used by the Chronicler (Archivator) to sort raw data into Divine Vectors.
"""

from enum import Enum
import re

class SacredVector(Enum):
    GENESIS = "GENESIS"       # Истоки, создание, инициализация
    COVENANT = "COVENANT"     # Контракты, протоколы, обещания
    CHRONICLE = "CHRONICLE"   # Логи, события, история, DEV_LOGS
    PSALM = "PSALM"           # Мысли, диалоги, рефлексия, voice
    LAW = "LAW"               # Код, правила, тесты, CI/CD
    UNKNOWN = "APOCRYPHA"     # Неопознанное

# Ключевые слова для распознавания векторов
VOCABULARY = {
    SacredVector.GENESIS: [
        r"genesis", r"init", r"bootstrap", r"start", r"begin", r"birth", 
        r"сотворение", r"начало", r"истоки", r"запуск"
    ],
    SacredVector.COVENANT: [
        r"contract", r"protocol", r"policy", r"agreement", r"rule", r"m\d+", 
        r"контракт", r"протокол", r"политика", r"завет", r"устав"
    ],
    SacredVector.CHRONICLE: [
        r"log", r"history", r"record", r"audit", r"trace", r"roadmap", 
        r"хроника", r"лог", r"история", r"запись", r"путь"
    ],
    SacredVector.PSALM: [
        r"thought", r"idea", r"voice", r"dialog", r"reflection", r"mind", r"heart",
        r"мысль", r"идея", r"диалог", r"рефлексия", r"сердце", r"душа"
    ],
    SacredVector.LAW: [
        r"code", r"def ", r"class ", r"import ", r"test", r"fix", r"patch",
        r"код", r"функция", r"тест", r"исправление", r"закон"
    ]
}

def discern_vector(text: str, filename: str) -> str:
    """Определяет, к какому Вектору относится текст или файл."""
    text_lower = text.lower()
    name_lower = filename.lower()
    
    scores = {v: 0 for v in SacredVector}
    
    for vector, patterns in VOCABULARY.items():
        for pattern in patterns:
            if re.search(pattern, name_lower):
                scores[vector] += 3
            if re.search(pattern, text_lower):
                scores[vector] += 1
                
    best_vector = max(scores, key=scores.get)
    if scores[best_vector] == 0:
        return SacredVector.UNKNOWN.value
        
    return best_vector.value
