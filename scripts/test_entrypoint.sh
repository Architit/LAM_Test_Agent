#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:---unit-only}"
PYTHON_BIN=""
export LAM_RUNTIME_LOG_FILE="${LAM_RUNTIME_LOG_FILE:-/tmp/$(basename "$ROOT")_LAM_RUNTIME_LOG.jsonl}"

resolve_python() {
  local candidates=(
    "$ROOT/.venv/bin/python"
    "$ROOT/../../.venv/bin/python"
    "${ECO_PYTHON_BIN:-}"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -z "$candidate" ]]; then
      continue
    fi
    if [[ -x "$candidate" ]] && "$candidate" -c "import pytest" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1 && python3 -c "import pytest" >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  return 1
}

PYTHON_BIN="$(resolve_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "[test-entrypoint] pytest unavailable"
  exit 2
fi

run_pytest() {
  "$PYTHON_BIN" -m pytest "$@"
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
