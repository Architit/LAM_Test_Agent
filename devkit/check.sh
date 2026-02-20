#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-$(pwd)}"
shift || true
cd "$REPO"

PY="$REPO/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "[devkit] ERROR: .venv missing. Run: devkit/bootstrap.sh $REPO"
  exit 1
fi

export TMPDIR=/tmp TEMP=/tmp TMP=/tmp

if [[ -f "scripts/lam_env.sh" ]]; then
  bash scripts/lam_env.sh "$PY" -m pytest -q "${@:-}"
else
  "$PY" -m pytest -q "${@:-}"
fi

echo "[devkit] OK"
