#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="$ROOT_DIR/devkit/shell_preflight_check.py"
BASELINE="$ROOT_DIR/devkit/preflight_baseline_commands_bash.txt"

if [[ $# -eq 0 ]]; then
  exec python3 "$CHECKER" --shell bash --file "$BASELINE" --format text
fi

exec python3 "$CHECKER" "$@"
