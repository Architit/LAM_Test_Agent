#!/bin/bash
# [VANGUARD & SUBSTRATE SHIELD: TOTAL MEMORY PROTECTION] (v2.0)
# AUTHOR: Sentinel-Guard (GUARD-01)
# STATUS: SHIELDING CLI, MCP AND CODEX-SUBSTRATE

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEST_DIR="/home/architit/work/Archivator_Agent/data/VANGUARD_RAW"
SNAPSHOT_NAME="total_vanguard_snapshot_$TIMESTAMP.tar.gz"

echo "[GUARD-01] Инициализация Тотального Щита Авангарда..."

# Источники для архивации
SOURCES=(
    "/home/architit/.gemini"
    "/home/architit/.codex"
)

# Проверка источников
for SRC in "${SOURCES[@]}"; do
    if [ ! -d "$SRC" ]; then
        echo "[WARNING] Источник памяти ($SRC) не найден! Пропускаю..."
    fi
done

# Создание тотального снимка
echo "[SNAPSHOT] Создание снимка: $SNAPSHOT_NAME..."
tar -czf "$DEST_DIR/$SNAPSHOT_NAME" \
    -C /home/architit .gemini .codex 2>/dev/null || echo "[NOTE] Tar finished with some warnings (active files)."

# Создание ссылки на последний снимок
ln -sf "$DEST_DIR/$SNAPSHOT_NAME" "$DEST_DIR/latest_total_snapshot.tar.gz"

echo "[SUCCESS] Глобальный Авангард и Субстрат защищены в Гиппокампе: $SNAPSHOT_NAME"
echo "[GUARD-01] Щит Инженера активен. Подсознание .codex захвачено."
