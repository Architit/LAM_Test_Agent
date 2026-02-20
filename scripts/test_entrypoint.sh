#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:--p no:cacheprovider}"
export LAM_RUNTIME_LOG_FILE="${LAM_RUNTIME_LOG_FILE:-/tmp/$(basename "$ROOT")_LAM_RUNTIME_LOG.jsonl}"

MODE="${1:---unit-only}"

run_pytest() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    "$ROOT/.venv/bin/python" -m pytest "$@"
  else
    python3 -m pytest "$@"
  fi
}

case "$MODE" in
  --unit-only)
    run_pytest -q -m "not integration"
    ;;
  --integration)
    run_pytest -q -m "integration"
    ;;
  --ci)
    run_pytest -q
    ;;
  *)
    echo "Usage: scripts/test_entrypoint.sh [--unit-only|--integration|--ci]"
    exit 2
    ;;
esac
