#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROVIDER_ENV_FILE="${LAM_PROVIDER_ENV_FILE:-$ROOT/scripts/provider-secrets.env}"
if [[ -f "$PROVIDER_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$PROVIDER_ENV_FILE"
fi
exec python3 "$ROOT/apps/lam_console/feedback_gateway.py" "$@"
