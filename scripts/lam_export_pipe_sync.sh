#!/usr/bin/env bash
# ==============================================================================
# RADRILONIUMA DATA EXPORT PIPE SYNC (v1.0)
# ==============================================================================
# Перекачивает данные из локальных экспортов агентов (WSL) 
# во внешние шлюзы (C:\data) и облачные маршруты.
# ==============================================================================
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WSL_BASE="/home/architit/work/LAM/data/export"
WIN_BASE="/mnt/c/data"
LOG_FILE="$ROOT/.gateway/hub/logs/export_pipe_sync.log"

log() {
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $1" >> "$LOG_FILE"
}

mkdir -p "$(dirname "$LOG_FILE")"

if [ ! -d "$WIN_BASE" ]; then
    log "ERROR: Windows export gateway $WIN_BASE not found. Aborting sync."
    exit 1
fi

log "START: Export Pipe Sync Cycle"

# 1. Синхронизация папок Агентов (WSL -> Windows)
for AGENT_DIR in "$WSL_BASE"/*/; do
    AGENT_NAME=$(basename "$AGENT_DIR")
    WIN_TARGET="$WIN_BASE/gateways/$AGENT_NAME"
    
    if [ -d "$AGENT_DIR" ]; then
        mkdir -p "$WIN_TARGET"
        # Используем rsync для эффективной перекачки
        rsync -a --delete "$AGENT_DIR/" "$WIN_TARGET/"
        log "Sync OK: Agent $AGENT_NAME -> Windows Gateway"
    fi
done

# 2. Агрегация для Облачных Маршрутов (Пример: все отчеты в Google Cloud)
# Здесь можно настроить специфические правила для каждой "трубы"
# Например, копируем все .md отчеты в папку google для облачной синхронизации
log "Cloud Routing: Aggregating reports for Google/Microsoft/Shinkai..."

find "$WSL_BASE" -name "*.md" -o -name "*.json" -mtime -1 -exec cp -t "$WIN_BASE/cloud/google/" {} + 2>/dev/null || true
find "$WSL_BASE" -name "*.md" -o -name "*.json" -mtime -1 -exec cp -t "$WIN_BASE/cloud/microsoft/" {} + 2>/dev/null || true

log "END: Export Pipe Sync Cycle Completed."
