#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-$(pwd)}"
cd "$REPO"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

PY="$REPO/.venv/bin/python"
PIP="$REPO/.venv/bin/pip"

"$PY" -m pip install -U pip

if [[ -f "requirements-dev.txt" ]]; then
  "$PIP" install -r requirements-dev.txt
elif [[ -f "requirements.txt" ]]; then
  "$PIP" install -r requirements.txt
elif [[ -f "pyproject.toml" ]]; then
  "$PIP" install -e .
else
  echo "[devkit] WARN: no requirements*.txt or pyproject.toml found"
fi

echo "[devkit] OK: $PY"

AUTOHEAL_SCRIPT="$REPO/devkit/healing_tools/gemini_gateway_autoheal.sh"
if [[ "${LARPAT_GATEWAY_AUTOHEAL:-1}" == "1" && -x "$AUTOHEAL_SCRIPT" ]]; then
  if "$AUTOHEAL_SCRIPT"; then
    echo "[devkit] Gateway auto-heal: OK"
  else
    if [[ "${LARPAT_GATEWAY_STRICT:-0}" == "1" ]]; then
      echo "[devkit] Gateway auto-heal: FAIL (strict mode)" >&2
      exit 1
    fi
    echo "[devkit] Gateway auto-heal: WARN (continuing; set LARPAT_GATEWAY_STRICT=1 to fail)" >&2
  fi
fi
