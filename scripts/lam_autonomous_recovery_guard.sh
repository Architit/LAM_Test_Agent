#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chmod +x "$ROOT/scripts/lam_autonomous_recovery_guard.py"
exec python3 "$ROOT/scripts/lam_autonomous_recovery_guard.py" "$@"
