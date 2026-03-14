#!/usr/bin/env bash
# ==============================================================================
# RADRILONIUMA OS BIOS BOOT MANAGER (v1.0)
# ==============================================================================
# Управляет тотальным запуском всех агентов, репозиториев, систем и модулей
# при старте устройства и подключении питания.
# ==============================================================================
set -e

BIOS_LOG="/home/architit/work/LAM_Test_Agent/.gateway/hub/logs/bios_boot_manager.log"
WORKSPACE_ROOT="/home/architit/work"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$(dirname "$BIOS_LOG")"
exec >> "$BIOS_LOG" 2>&1

echo "================================================================="
echo "[BIOS BOOT] Инициализация RADRILONIUMA OS BIOS BOOT MANAGER"
echo "[BIOS BOOT] Время: $TIMESTAMP"
echo "[BIOS BOOT] Питание подключено. Запуск последовательности."
echo "================================================================="

# 0. Верификация труб экспорта (Data Pipes)
echo "[BIOS BOOT] 0. Проверка шлюзов экспорта (WSL <-> Windows)..."
WSL_EXPORT="/home/architit/work/LAM/data/export"
WIN_EXPORT="/mnt/c/data"

if [ ! -d "$WIN_EXPORT" ]; then
    echo "[WARNING] Шлюз C:\data не доступен через /mnt/c/data!"
else
    echo "[BIOS BOOT] Шлюз Windows активен."
    mkdir -p "$WIN_EXPORT/cloud/google" "$WIN_EXPORT/cloud/microsoft" "$WIN_EXPORT/cloud/ollama" "$WIN_EXPORT/cloud/shinkai"
fi

# 1. Запуск базового моста ядра (LAM_Test_Agent)
echo "[BIOS BOOT] 1. Старт ядра (Core Stack & Recovery Guard)..."
if [ -x "$WORKSPACE_ROOT/LAM_Test_Agent/scripts/lam_bridge_stack.sh" ]; then
    "$WORKSPACE_ROOT/LAM_Test_Agent/scripts/lam_bridge_stack.sh" start
    echo "[BIOS BOOT] Стек LAM_Test_Agent запущен."
fi

# 2. Обход всех 24 Органов и Агентов
echo "[BIOS BOOT] 2. Сканирование и пробуждение суверенных деревьев (24 Органа)..."
for ORGAN_DIR in "$WORKSPACE_ROOT"/*/; do
    ORGAN_NAME=$(basename "$ORGAN_DIR")
    
    # Игнорируем технические директории
    if [[ "$ORGAN_NAME" == .* || "$ORGAN_NAME" == "data" || "$ORGAN_NAME" == "lam-wheelhouse" ]]; then
        continue
    fi

    echo "[BIOS BOOT] Проверка органа: $ORGAN_NAME"

    # Ищем стандартные триггеры запуска AESS
    if [ -x "$ORGAN_DIR/scripts/aess_autostart.sh" ]; then
        echo "  -> Найден AESS Autostart. Запускаем..."
        (cd "$ORGAN_DIR" && ./scripts/aess_autostart.sh) &
    fi

    # Ищем специфичные bridge-стеки
    if [ -x "$ORGAN_DIR/scripts/lam_bridge_stack.sh" ] && [ "$ORGAN_NAME" != "LAM_Test_Agent" ]; then
        echo "  -> Найден Bridge Stack. Запускаем..."
        (cd "$ORGAN_DIR" && ./scripts/lam_bridge_stack.sh start) &
    fi
    
    # Ищем Python-демоны автопилота
    if [ -x "$ORGAN_DIR/scripts/lam_autonomous_recovery_guard.sh" ] && [ "$ORGAN_NAME" != "LAM_Test_Agent" ]; then
        echo "  -> Найден Recovery Guard. Запускаем..."
        (cd "$ORGAN_DIR" && ./scripts/lam_autonomous_recovery_guard.sh &) 
    fi
done

wait
echo "[BIOS BOOT] Все сигналы пробуждения отправлены."

# 3. Синхронизация глобального циркулирования
echo "[BIOS BOOT] 3. Форсированный пульс циркуляции (Full Forest Sync)..."
if [ -x "$WORKSPACE_ROOT/LAM_Test_Agent/scripts/lam_realtime_circulation.sh" ]; then
    "$WORKSPACE_ROOT/LAM_Test_Agent/scripts/lam_realtime_circulation.sh" --once || true
fi


# 4. Запуск Глобального Автопилота на Мосту (Bridge)
echo "[BIOS BOOT] 4. Инициализация автопилота RADRILONIUMA (Directive & Report)..."
if [ -d "$WORKSPACE_ROOT/RADRILONIUMA" ]; then
    (cd "$WORKSPACE_ROOT/RADRILONIUMA" && nohup python3 scripts/directive_autopilot.py >> .gateway/hub/logs/directive_autopilot.log 2>&1 &)
    (cd "$WORKSPACE_ROOT/RADRILONIUMA" && nohup python3 scripts/report_autopilot.py >> .gateway/hub/logs/report_autopilot.log 2>&1 &)
    echo "[BIOS BOOT] Автопилоты Моста запущены."
fi

echo "[BIOS BOOT] ====================================================="
echo "[BIOS BOOT] ПОСЛЕДОВАТЕЛЬНОСТЬ BIOS ЗАВЕРШЕНА УСПЕШНО."
echo "[BIOS BOOT] ОС RADRILONIUMA СТАРТОВАЛА КАК ЧАСЫ. ⚜️"
echo "[BIOS BOOT] ====================================================="
