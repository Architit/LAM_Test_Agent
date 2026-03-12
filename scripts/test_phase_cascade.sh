#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTEST_BIN="python3 -m pytest"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTEST_BIN="$ROOT/.venv/bin/python -m pytest"
fi

STATE_DIR="${LAM_TEST_STATE_DIR:-$ROOT/.gateway/test_runs}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$STATE_DIR/$RUN_ID"
SUMMARY_FILE="$RUN_DIR/summary.json"
mkdir -p "$RUN_DIR"

MODE="${1:---standard}"

phase_names=()
phase_cmds=()

add_phase() {
  phase_names+=("$1")
  phase_cmds+=("$2")
}

case "$MODE" in
  --quick)
    add_phase "phase-00-smoke" "$PYTEST_BIN -q tests/test_runtime_smoke.py tests/test_test_entrypoint_contract.py"
    add_phase "phase-10-unit-core" "$PYTEST_BIN -q tests/unit/test_lam_console_core.py tests/unit/test_lam_gateway.py tests/unit/test_lam_model_worker.py tests/unit/test_mcp_watchdog.py tests/unit/test_gws_bridge.py"
    ;;
  --standard)
    add_phase "phase-00-smoke" "$PYTEST_BIN -q tests/test_runtime_smoke.py tests/test_test_entrypoint_contract.py"
    add_phase "phase-10-unit-core" "$PYTEST_BIN -q tests/unit/test_lam_console_core.py tests/unit/test_lam_gateway.py tests/unit/test_lam_model_worker.py tests/unit/test_mcp_watchdog.py tests/unit/test_gws_bridge.py"
    add_phase "phase-20-unit-all" "$PYTEST_BIN -q -m 'unit and not submodule_required'"
    add_phase "phase-30-regression-gates" "$PYTEST_BIN -q tests/test_phase_b_patch_runtime_contract.py tests/test_phase_c_memory_kickoff.py tests/test_phase_d_transport_regression.py tests/test_phase_e_flow_control_regression.py tests/test_phase_f_p0_safety_regression.py tests/test_phase_r_research_gate_regression.py"
    add_phase "phase-40-integration" "$PYTEST_BIN -q -m integration"
    ;;
  --full)
    add_phase "phase-00-smoke" "$PYTEST_BIN -q tests/test_runtime_smoke.py tests/test_test_entrypoint_contract.py"
    add_phase "phase-10-unit-all" "$PYTEST_BIN -q -m 'not integration and not submodule_required'"
    add_phase "phase-20-integration" "$PYTEST_BIN -q -m integration"
    add_phase "phase-30-full-suite" "$PYTEST_BIN -q"
    ;;
  *)
    echo "Usage: scripts/test_phase_cascade.sh [--quick|--standard|--full]" >&2
    exit 2
    ;;
esac

printf '{\n  "run_id": "%s",\n  "mode": "%s",\n  "root": "%s",\n  "started_utc": "%s",\n  "phases": [\n' \
  "$RUN_ID" "$MODE" "$ROOT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$SUMMARY_FILE"

phase_count="${#phase_names[@]}"
for i in "${!phase_names[@]}"; do
  name="${phase_names[$i]}"
  cmd="${phase_cmds[$i]}"
  log_file="$RUN_DIR/${name}.log"
  ts_start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "[test-cascade] START $name"
  echo "[test-cascade] CMD   $cmd"

  set +e
  bash -lc "$cmd" >"$log_file" 2>&1
  rc=$?
  set -e

  ts_end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ "$rc" -eq 0 ]]; then
    status="passed"
    echo "[test-cascade] PASS  $name"
  else
    status="failed"
    echo "[test-cascade] FAIL  $name rc=$rc log=$log_file"
  fi

  comma=","
  if [[ "$i" -eq $((phase_count - 1)) ]]; then
    comma=""
  fi

  printf '    {"phase":"%s","status":"%s","rc":%d,"start_utc":"%s","end_utc":"%s","log":"%s"}%s\n' \
    "$name" "$status" "$rc" "$ts_start" "$ts_end" "$log_file" "$comma" >> "$SUMMARY_FILE"

  if [[ "$rc" -ne 0 ]]; then
    break
  fi
done

printf '  ],\n  "finished_utc": "%s"\n}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SUMMARY_FILE"

echo "[test-cascade] summary: $SUMMARY_FILE"
