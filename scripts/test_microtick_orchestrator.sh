#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTEST_BIN="python3 -m pytest"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTEST_BIN="$ROOT/.venv/bin/python -m pytest"
fi

STATE_DIR="${LAM_TEST_STATE_DIR:-$ROOT/.gateway/test_runs}"
MODE="${1:---standard}"
RUN_ID="${LAM_TEST_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_DIR="$STATE_DIR/$RUN_ID"
TICK_DIR="$RUN_DIR/ticks"
PROGRESS_FILE="$RUN_DIR/microtick_progress.tsv"
SUMMARY_FILE="$RUN_DIR/microtick_summary.json"
ISOLATION_ROOT="${LAM_TEST_ISOLATION_ROOT:-$ROOT/.gateway/test_zones}"
ISOLATION_ENABLED="${LAM_TEST_ISOLATE_WORKSPACE:-1}"
FS_LOCK_ENABLED="${LAM_TEST_FS_LOCK_ENABLED:-1}"
WORKSPACE_DIR="$ISOLATION_ROOT/$RUN_ID/workspace"
LOCKS_FILE="$ISOLATION_ROOT/$RUN_ID/locks.tsv"
ZONES_FILE="$ISOLATION_ROOT/$RUN_ID/zones.tsv"
TICK_TIMEOUT_SEC="${LAM_TEST_TICK_TIMEOUT_SEC:-120}"
MAX_TICKS="${LAM_TEST_MAX_TICKS:-0}"
RESUME="${LAM_TEST_RESUME:-1}"

mkdir -p "$TICK_DIR"
mkdir -p "$ISOLATION_ROOT/$RUN_ID"

if [[ ! -f "$LOCKS_FILE" ]]; then
  printf "tick\tscope\tstatus\tts_utc\n" > "$LOCKS_FILE"
fi
if [[ ! -f "$ZONES_FILE" ]]; then
  printf "tick\tzone\tphase\tscope\tstatus\tstart_utc\tend_utc\tlog\n" > "$ZONES_FILE"
fi

plan_names=()
plan_cmds=()
plan_scopes=()
current_lock_paths=()
current_lock_modes=()

add_tick() {
  plan_names+=("$1")
  plan_cmds+=("$2")
  plan_scopes+=("${3:-}")
}

add_file_ticks() {
  local phase="$1"
  local marker="$2"
  shift 2
  local file
  for file in "$@"; do
    [[ -f "$file" ]] || continue
    if [[ -n "$marker" ]]; then
      add_tick "$phase::$(basename "$file")" "$PYTEST_BIN -q -m '$marker' '$file'" "$file"
    else
      add_tick "$phase::$(basename "$file")" "$PYTEST_BIN -q '$file'" "$file"
    fi
  done
}

collect_standard_plan() {
  add_tick "phase-00::runtime-smoke" "$PYTEST_BIN -q tests/test_runtime_smoke.py tests/test_test_entrypoint_contract.py" "tests/test_runtime_smoke.py,tests/test_test_entrypoint_contract.py"

  mapfile -t core_files < <(printf '%s\n' \
    tests/unit/test_lam_console_core.py \
    tests/unit/test_lam_gateway.py \
    tests/unit/test_lam_model_worker.py \
    tests/unit/test_mcp_watchdog.py \
    tests/unit/test_gws_bridge.py)
  add_file_ticks "phase-10-core" "" "${core_files[@]}"

  mapfile -t unit_files < <(find tests/unit -maxdepth 1 -type f -name 'test_*.py' | sort)
  add_file_ticks "phase-20-unit" "unit and not submodule_required" "${unit_files[@]}"

  mapfile -t reg_files < <(printf '%s\n' \
    tests/test_phase_b_patch_runtime_contract.py \
    tests/test_phase_c_memory_kickoff.py \
    tests/test_phase_d_transport_regression.py \
    tests/test_phase_e_flow_control_regression.py \
    tests/test_phase_f_p0_safety_regression.py \
    tests/test_phase_r_research_gate_regression.py)
  add_file_ticks "phase-30-regression" "" "${reg_files[@]}"

  mapfile -t int_files < <(find tests/it -maxdepth 1 -type f -name 'test_*.py' | sort)
  add_file_ticks "phase-40-integration" "integration" "${int_files[@]}"
}

collect_quick_plan() {
  add_tick "phase-00::runtime-smoke" "$PYTEST_BIN -q tests/test_runtime_smoke.py tests/test_test_entrypoint_contract.py" "tests/test_runtime_smoke.py,tests/test_test_entrypoint_contract.py"
  mapfile -t core_files < <(printf '%s\n' \
    tests/unit/test_lam_console_core.py \
    tests/unit/test_lam_gateway.py \
    tests/unit/test_lam_model_worker.py \
    tests/unit/test_mcp_watchdog.py \
    tests/unit/test_gws_bridge.py)
  add_file_ticks "phase-10-core" "" "${core_files[@]}"
}

collect_full_plan() {
  collect_standard_plan
  add_tick "phase-90-full-suite" "$PYTEST_BIN -q" "."
}

prepare_isolated_workspace() {
  if [[ "$ISOLATION_ENABLED" != "1" ]]; then
    return 0
  fi
  if [[ -d "$WORKSPACE_DIR" ]]; then
    return 0
  fi
  mkdir -p "$WORKSPACE_DIR"
  rsync -a --delete \
    --exclude=".git" \
    --exclude=".venv" \
    --exclude=".gateway/test_runs" \
    --exclude=".gateway/test_zones" \
    "$ROOT/" "$WORKSPACE_DIR/"
}

clear_current_locks() {
  current_lock_paths=()
  current_lock_modes=()
}

unlock_current_locks() {
  local idx
  for idx in "${!current_lock_paths[@]}"; do
    local p="${current_lock_paths[$idx]}"
    local m="${current_lock_modes[$idx]}"
    if [[ -n "$m" && -e "$p" ]]; then
      chmod "$m" "$p" 2>/dev/null || true
    fi
  done
  clear_current_locks
}

lock_scope_paths() {
  local tick_no="$1"
  local scope_csv="$2"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  clear_current_locks
  IFS=',' read -r -a scopes <<<"$scope_csv"
  local scope
  for scope in "${scopes[@]}"; do
    scope="$(echo "$scope" | xargs)"
    [[ -n "$scope" ]] || continue
    printf "%s\t%s\tactive\t%s\n" "$tick_no" "$scope" "$ts" >> "$LOCKS_FILE"
    if [[ "$FS_LOCK_ENABLED" == "1" ]]; then
      local full="$ROOT/$scope"
      if [[ -e "$full" ]]; then
        local mode
        mode="$(stat -c '%a' "$full" 2>/dev/null || true)"
        if chmod a-w "$full" 2>/dev/null; then
          current_lock_paths+=("$full")
          current_lock_modes+=("$mode")
        fi
      fi
    fi
  done
}

mark_scope_released() {
  local tick_no="$1"
  local scope_csv="$2"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  IFS=',' read -r -a scopes <<<"$scope_csv"
  local scope
  for scope in "${scopes[@]}"; do
    scope="$(echo "$scope" | xargs)"
    [[ -n "$scope" ]] || continue
    printf "%s\t%s\treleased\t%s\n" "$tick_no" "$scope" "$ts" >> "$LOCKS_FILE"
  done
}

case "$MODE" in
  --quick) collect_quick_plan ;;
  --standard) collect_standard_plan ;;
  --full) collect_full_plan ;;
  *)
    echo "Usage: scripts/test_microtick_orchestrator.sh [--quick|--standard|--full]" >&2
    exit 2
    ;;
esac

prepare_isolated_workspace

cleanup() {
  unlock_current_locks || true
}
trap cleanup EXIT INT TERM

if [[ ! -f "$PROGRESS_FILE" ]]; then
  printf "tick\tphase\tstatus\trc\tstart_utc\tend_utc\tlog\n" > "$PROGRESS_FILE"
fi

executed=0
failed=0
for i in "${!plan_names[@]}"; do
  tick_no=$((i + 1))
  name="${plan_names[$i]}"
  cmd="${plan_cmds[$i]}"
  scope="${plan_scopes[$i]}"
  log_file="$TICK_DIR/tick_$(printf '%04d' "$tick_no").log"
  phase="${name%%::*}"
  zone_dir="$ISOLATION_ROOT/$RUN_ID/tick_$(printf '%04d' "$tick_no")"
  work_root="$ROOT"
  if [[ "$ISOLATION_ENABLED" == "1" ]]; then
    work_root="$WORKSPACE_DIR"
  fi

  if [[ "$RESUME" == "1" ]] && [[ -f "$PROGRESS_FILE" ]] && rg -q "^${tick_no}\t" "$PROGRESS_FILE"; then
    echo "[microtick] SKIP tick=$tick_no (already recorded)"
    continue
  fi

  ts_start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "[microtick] START tick=$tick_no name=$name"
  echo "[microtick] CMD   $cmd"
  if [[ -n "$scope" ]]; then
    lock_scope_paths "$tick_no" "$scope"
  fi
  mkdir -p "$zone_dir"
  set +e
  timeout "${TICK_TIMEOUT_SEC}s" bash -lc "cd '$work_root' && $cmd" >"$log_file" 2>&1
  rc=$?
  set -e
  if [[ -n "$scope" ]]; then
    mark_scope_released "$tick_no" "$scope"
  fi
  unlock_current_locks
  ts_end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ "$rc" -eq 0 ]]; then
    status="passed"
    echo "[microtick] PASS  tick=$tick_no name=$name"
  elif [[ "$rc" -eq 124 ]]; then
    status="timeout"
    failed=1
    echo "[microtick] TIMEOUT tick=$tick_no name=$name log=$log_file"
  else
    status="failed"
    failed=1
    echo "[microtick] FAIL  tick=$tick_no name=$name rc=$rc log=$log_file"
  fi

  printf "%d\t%s\t%s\t%d\t%s\t%s\t%s\n" \
    "$tick_no" "$phase" "$status" "$rc" "$ts_start" "$ts_end" "$log_file" >> "$PROGRESS_FILE"
  printf "%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$tick_no" "$zone_dir" "$phase" "${scope:-}" "$status" "$ts_start" "$ts_end" "$log_file" >> "$ZONES_FILE"

  executed=$((executed + 1))
  if [[ "$failed" -ne 0 ]]; then
    break
  fi
  if [[ "$MAX_TICKS" -gt 0 ]] && [[ "$executed" -ge "$MAX_TICKS" ]]; then
    echo "[microtick] pause: reached MAX_TICKS=$MAX_TICKS"
    break
  fi
done

passed_count="$(awk -F'\t' 'NR>1 && $3=="passed"{c++} END{print c+0}' "$PROGRESS_FILE")"
failed_count="$(awk -F'\t' 'NR>1 && ($3=="failed" || $3=="timeout"){c++} END{print c+0}' "$PROGRESS_FILE")"
total_count="$(awk 'END{print NR-1}' "$PROGRESS_FILE")"

cat > "$SUMMARY_FILE" <<EOF
{
  "run_id": "$RUN_ID",
  "mode": "$MODE",
  "isolation_enabled": $([[ "$ISOLATION_ENABLED" == "1" ]] && echo true || echo false),
  "fs_lock_enabled": $([[ "$FS_LOCK_ENABLED" == "1" ]] && echo true || echo false),
  "isolation_workspace": "$WORKSPACE_DIR",
  "locks_file": "$LOCKS_FILE",
  "zones_file": "$ZONES_FILE",
  "tick_timeout_sec": $TICK_TIMEOUT_SEC,
  "total_recorded_ticks": $total_count,
  "passed_ticks": $passed_count,
  "failed_ticks": $failed_count,
  "progress_file": "$PROGRESS_FILE",
  "generated_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "[microtick] summary: $SUMMARY_FILE"
if [[ "$failed" -ne 0 ]]; then
  exit 1
fi
