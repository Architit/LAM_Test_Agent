#!/bin/bash
# [CIRCULATION PROTOCOL: EXECUTOR SINEW] (v1.0)
# AUTHOR: Sentinel-Guard (GUARD-01)
# STATUS: CONNECTING THE ENGINEER TO THE TRINITY

set -e

echo "[GUARD-01] Инициализация исполнительного контура..."

# Базовые пути
BASE_DIR="/home/architit/work"
OPERATOR_DIR="$BASE_DIR/Operator_Agent"
CODEX_DIR="$BASE_DIR/LAM-Codex_Agent"
ARCHIVATOR_DIR="$BASE_DIR/Archivator_Agent"

# ФУНКЦИЯ ПРОВЕРКИ/СОЗДАНИЯ СИМЛИНКА
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

# 1. СВЯЗЬ: ОПЕРАТОР -> ИНЖЕНЕР (ЗАДАЧИ)
echo "[LINKING] Подключение Фронтальной коры к Инженеру..."
link_circuit "$OPERATOR_DIR/data/export" "$CODEX_DIR/data/import" "Operator Outbox -> Codex Inbox"

# 2. СВЯЗЬ: ИНЖЕНЕР -> ПАМЯТЬ (ОТЧЕТЫ)
echo "[LINKING] Подключение Инженера к Гиппокампу..."
link_circuit "$CODEX_DIR/data/export" "$ARCHIVATOR_DIR/data/import" "Codex Outbox -> Global Memory Data"

echo "[GUARD-01] Сварка исполнительных контактов завершена. Инженер подключен к Триаде."
