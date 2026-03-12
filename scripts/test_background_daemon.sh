#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${LAM_BG_TEST_STATE_DIR:-$ROOT/.gateway/test_runs/background}"
PID_FILE="$STATE_DIR/daemon.pid"
LOG_FILE="$STATE_DIR/daemon.log"
ERRORS_FILE="$STATE_DIR/errors.jsonl"
RUNTIME_FILE="$STATE_DIR/runtime.env"
LAST_NOTIFIED_FILE="$STATE_DIR/last_notified_failure.txt"

mkdir -p "$STATE_DIR"

MODE="${LAM_BG_TEST_MODE:---standard}"
TICK_TIMEOUT_SEC="${LAM_BG_TEST_TICK_TIMEOUT_SEC:-120}"
MAX_TICKS_PER_CYCLE="${LAM_BG_TEST_MAX_TICKS_PER_CYCLE:-1}"
SLEEP_SEC="${LAM_BG_TEST_SLEEP_SEC:-8}"
RUN_ID="${LAM_BG_TEST_RUN_ID:-bg_$(date -u +%Y%m%dT%H%M%SZ)}"

usage() {
  cat <<'EOF'
Usage:
  scripts/test_background_daemon.sh start [--mode quick|standard|full] [--tick-timeout SEC] [--max-ticks N] [--sleep-sec SEC]
  scripts/test_background_daemon.sh stop
  scripts/test_background_daemon.sh status
  scripts/test_background_daemon.sh errors [--lines N]
  scripts/test_background_daemon.sh watch

Notes:
  - Non-blocking microtick testing daemon.
  - Runs test ticks in small chunks and records failures in realtime.
EOF
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1
}

save_runtime() {
  cat > "$RUNTIME_FILE" <<EOF
MODE=$MODE
TICK_TIMEOUT_SEC=$TICK_TIMEOUT_SEC
MAX_TICKS_PER_CYCLE=$MAX_TICKS_PER_CYCLE
SLEEP_SEC=$SLEEP_SEC
RUN_ID=$RUN_ID
EOF
}

load_runtime() {
  if [[ -f "$RUNTIME_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$RUNTIME_FILE"
  fi
}

emit_failure_event() {
  local progress_file="$1"
  [[ -f "$progress_file" ]] || return 0
  local fail_line
  fail_line="$(awk -F'\t' 'NR>1 && ($3=="failed" || $3=="timeout"){line=$0} END{print line}' "$progress_file")"
  [[ -n "$fail_line" ]] || return 0

  local last_notified=""
  [[ -f "$LAST_NOTIFIED_FILE" ]] && last_notified="$(cat "$LAST_NOTIFIED_FILE")"
  if [[ "$fail_line" == "$last_notified" ]]; then
    return 0
  fi

  local tick phase status rc start_utc end_utc log_file
  IFS=$'\t' read -r tick phase status rc start_utc end_utc log_file <<<"$fail_line"
  local excerpt=""
  if [[ -f "$log_file" ]]; then
    excerpt="$(tail -n 40 "$log_file" | sed 's/"/\\"/g' | tr '\n' ' ' | cut -c1-1200)"
  fi

  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '{"ts_utc":"%s","run_id":"%s","tick":%s,"phase":"%s","status":"%s","rc":%s,"log":"%s","excerpt":"%s"}\n' \
    "$ts" "$RUN_ID" "$tick" "$phase" "$status" "$rc" "$log_file" "$excerpt" >> "$ERRORS_FILE"
  printf '%s' "$fail_line" > "$LAST_NOTIFIED_FILE"
}

worker_loop() {
  save_runtime
  echo "[bg-test] started mode=$MODE run_id=$RUN_ID timeout=$TICK_TIMEOUT_SEC max_ticks=$MAX_TICKS_PER_CYCLE sleep=$SLEEP_SEC"
  while true; do
    local run_dir="$ROOT/.gateway/test_runs/$RUN_ID"
    local progress_file="$run_dir/microtick_progress.tsv"

    set +e
    LAM_TEST_RUN_ID="$RUN_ID" \
    LAM_TEST_MAX_TICKS="$MAX_TICKS_PER_CYCLE" \
    LAM_TEST_TICK_TIMEOUT_SEC="$TICK_TIMEOUT_SEC" \
    LAM_TEST_RESUME=1 \
    "$ROOT/scripts/test_microtick_orchestrator.sh" "$MODE" >>"$LOG_FILE" 2>&1
    local rc=$?
    set -e

    if [[ "$rc" -ne 0 ]]; then
      emit_failure_event "$progress_file"
    fi
    sleep "$SLEEP_SEC"
  done
}

start_daemon() {
  if is_running; then
    echo "[bg-test] already running pid=$(cat "$PID_FILE")"
    return 0
  fi
  : > "$LOG_FILE"
  nohup "$0" _worker >"$LOG_FILE" 2>&1 &
  echo "$!" > "$PID_FILE"
  echo "[bg-test] daemon started pid=$(cat "$PID_FILE")"
}

stop_daemon() {
  if ! is_running; then
    echo "[bg-test] not running"
    rm -f "$PID_FILE"
    return 0
  fi
  kill "$(cat "$PID_FILE")" || true
  rm -f "$PID_FILE"
  echo "[bg-test] daemon stopped"
}

status_daemon() {
  load_runtime
  if is_running; then
    echo "[bg-test] running pid=$(cat "$PID_FILE") mode=${MODE:-unknown} run_id=${RUN_ID:-unknown}"
  else
    echo "[bg-test] stopped"
  fi
  if [[ -f "$ERRORS_FILE" ]]; then
    echo "[bg-test] errors_file=$ERRORS_FILE"
  fi
  return 0
}

show_errors() {
  local lines="${1:-60}"
  [[ -f "$ERRORS_FILE" ]] || { echo "[bg-test] no errors file yet"; return 0; }
  tail -n "$lines" "$ERRORS_FILE"
}

watch_errors() {
  [[ -f "$ERRORS_FILE" ]] || touch "$ERRORS_FILE"
  tail -n 40 -f "$ERRORS_FILE"
}

if [[ "${1:-}" == "_worker" ]]; then
  shift || true
  load_runtime
  worker_loop
  exit 0
fi

CMD="${1:-status}"
shift || true

if [[ "$CMD" == "start" ]]; then
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode) MODE="--$2"; shift 2 ;;
      --tick-timeout) TICK_TIMEOUT_SEC="$2"; shift 2 ;;
      --max-ticks) MAX_TICKS_PER_CYCLE="$2"; shift 2 ;;
      --sleep-sec) SLEEP_SEC="$2"; shift 2 ;;
      *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
  done
fi

case "$CMD" in
  start) start_daemon ;;
  stop) stop_daemon ;;
  status) status_daemon ;;
  errors)
    if [[ "${1:-}" == "--lines" ]]; then
      show_errors "${2:-60}"
    else
      show_errors 60
    fi
    ;;
  watch) watch_errors ;;
  *)
    usage
    exit 2
    ;;
esac
