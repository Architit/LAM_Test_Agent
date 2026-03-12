#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO_ROOT="${LAM_TEST_ISOLATION_ROOT:-$ROOT/.gateway/test_zones}"
RUN_ID="${1:-}"

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(ls -1dt "$ISO_ROOT"/* 2>/dev/null | head -n1 | xargs -r basename)"
fi

if [[ -z "$RUN_ID" || ! -d "$ISO_ROOT/$RUN_ID" ]]; then
  echo "[isolation] no runs found"
  exit 0
fi

LOCKS="$ISO_ROOT/$RUN_ID/locks.tsv"
ZONES="$ISO_ROOT/$RUN_ID/zones.tsv"

echo "[isolation] run_id=$RUN_ID"
[[ -f "$LOCKS" ]] && echo "[isolation] locks_file=$LOCKS"
[[ -f "$ZONES" ]] && echo "[isolation] zones_file=$ZONES"

if [[ -f "$LOCKS" ]]; then
  echo "[isolation] active_locks:"
  awk -F'\t' 'NR>1 && $3=="active"{print " - tick=" $1 " scope=" $2 " ts=" $4}' "$LOCKS" || true
fi

if [[ -f "$ZONES" ]]; then
  echo "[isolation] latest_zones:"
  tail -n 12 "$ZONES"
fi
