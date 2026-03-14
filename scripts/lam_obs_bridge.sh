#!/usr/bin/env bash
set -euo pipefail

# Datadog LLM Observability Wrapper for LAM Captain Bridge
# Authorized by Global Administrator

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Configuration
export DD_LLMOBS_ENABLED=1
export DD_LLMOBS_ML_APP="Interactionface_Arrierguard_2026"
export DD_API_KEY="9d786ecfa35d998ede2643577bb39eae"
export DD_SITE="datadoghq.com"

echo "[observability] Activating Datadog LLM Observability for Captain's Bridge..."
echo "[observability] App: $DD_LLMOBS_ML_APP"

# Use the virtual environment's ddtrace-run if available
DDTRACE_RUN="$ROOT/.venv/bin/ddtrace-run"
if [[ ! -f "$DDTRACE_RUN" ]]; then
    DDTRACE_RUN="ddtrace-run"
fi

exec "$DDTRACE_RUN" python3 "$ROOT/apps/lam_console/app.py" "$@"
