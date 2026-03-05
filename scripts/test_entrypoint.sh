#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:--p no:cacheprovider}"
export LAM_RUNTIME_LOG_FILE="${LAM_RUNTIME_LOG_FILE:-/tmp/$(basename "$ROOT")_LAM_RUNTIME_LOG.jsonl}"

run_pytest() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    "$ROOT/.venv/bin/python" -m pytest "$@"
  else
    python3 -m pytest "$@"
  fi
}

MODE="${1:---all}"

case "$MODE" in
  --all)
    run_pytest -q
    ;;
  --unit-only)
    run_pytest -q -m "not integration"
    ;;
  --integration)
    run_pytest -q -m "integration"
    ;;
  --governance)
    run_pytest -q -k governance
    ;;
  --patch-runtime)
    run_pytest -q tests/test_phase_b_patch_runtime_contract.py
    ;;
  --memory)
    run_pytest -q tests/test_phase_c_memory_kickoff.py tests/test_phase_b_patch_runtime_contract.py
    ;;
  --transport)
    run_pytest -q tests/test_phase_d_transport_regression.py tests/test_phase_b_patch_runtime_contract.py
    ;;
  --ci)
    run_pytest -q
    ;;
  *)
    echo "Usage: scripts/test_entrypoint.sh [--all|--unit-only|--integration|--governance|--patch-runtime|--memory|--transport|--ci]"
    exit 2
    ;;
esac
