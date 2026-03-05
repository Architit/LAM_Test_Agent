#!/bin/bash
# [CIRCULATION PROTOCOL: TRINITY SINEW] (v1.0)
# AUTHOR: Sentinel-Guard (GUARD-01)
# STATUS: INITIALIZING HYBRID TRANSPORT

set -e

echo "[GUARD-01] Инициализация кровеносной системы Триады..."

# Базовые пути (абсолютные)
BASE_DIR="/home/architit/work"
HEART_DIR="$BASE_DIR/Trianiuma"
MEMORY_DIR="$BASE_DIR/Archivator_Agent"
OPERATOR_DIR="$BASE_DIR/Operator_Agent"

# ФУНКЦИЯ ПРОВЕРКИ/СОЗДАНИЯ СИМЛИНКА (PRECISION SCOPING)
link_circuit() {
    local src=$1
    local dest=$2
    local label=$3
    if [ -e "$src" ]; then
        ln -sf "$src" "$dest"
        echo "[SUCCESS] Связь установлена: $label"
    else
        echo "[ERROR] Исходный узел $src не найден для $label"
    fi
}

# 1. СВЯЗЬ: ОПЕРАТОР <-> СЕРДЦЕ (ЯДРО И МАНИФЕСТ)
echo "[LINKING] Оператор подключается к Сердцу..."
link_circuit "$HEART_DIR/RADRILONIUMA_MANIFESTO.md" "$OPERATOR_DIR/matrix/MANIFESTO.md" "Heart Manifesto -> Operator Matrix"

# 2. СВЯЗЬ: ОПЕРАТОР <-> ПАМЯТЬ (СЕМАНТИКА)
echo "[LINKING] Оператор подключается к Гиппокампу..."
link_circuit "$MEMORY_DIR/matrix" "$OPERATOR_DIR/matrix/GLOBAL_MEMORY" "Global Memory -> Operator Matrix"

# 3. СВЯЗЬ: ПАМЯТЬ <-> ОПЕРАТОР (ИСТОРИЯ И ОЧЕРЕДИ)
echo "[LINKING] Гиппокамп подключается к Фронтальной коре..."
link_circuit "$OPERATOR_DIR/chronolog" "$MEMORY_DIR/data/OPERATOR_HISTORY" "Operator History -> Global Memory Data"
link_circuit "$OPERATOR_DIR/data/export" "$MEMORY_DIR/data/OPERATOR_OUTBOX" "Operator Outbox -> Global Memory Data"

echo "[GUARD-01] Сварка контактов завершена. Триада объединена."
