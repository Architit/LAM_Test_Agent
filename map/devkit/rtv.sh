#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_ROOT="${ECO_WORK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
LAM_DIR="${LAM_DIR:-$WORK_ROOT/LAM}"
RO_DIR="${RO_DIR:-$WORK_ROOT/Roaudter-agent}"

cd "$RO_DIR"
pip install -e . >/dev/null

cd "$LAM_DIR"
export TMPDIR=/tmp TEMP=/tmp TMP=/tmp
export ROAUDTER_TRACE="${ROAUDTER_TRACE:-1}"
export ROAUDTER_TRACE_ONLY="${ROAUDTER_TRACE_ONLY:-nonok}"

# -s shows prints even on success
bash scripts/lam_env.sh pytest -q -s -k "${1:-roaudter}"
