#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_ROOT="${ECO_WORK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ROOT_LAM="${LAM_DIR:-$WORK_ROOT/LAM}"
export TMPDIR=/tmp TEMP=/tmp TMP=/tmp
bash "$ROOT_LAM/scripts/lam_env.sh" "$@"
