#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

repo_is_dirty() {
  local repo="$1"
  if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 1
  fi

  if ! git -C "$repo" diff --quiet --ignore-submodules --; then
    return 0
  fi
  if ! git -C "$repo" diff --cached --quiet --ignore-submodules --; then
    return 0
  fi
  if [[ -n "$(git -C "$repo" ls-files --others --exclude-standard)" ]]; then
    return 0
  fi
  return 1
}

prepare_clone_destination() {
  local dst="$1"
  if [[ ! -e "$dst" ]]; then
    return 0
  fi

  if [[ -d "$dst/.git" ]] && repo_is_dirty "$dst"; then
    echo "[bootstrap] refusing to remove dirty destination: $dst"
    echo "[bootstrap] resolve manually (stash/commit/clean) before bootstrap retry"
    return 1
  fi

  rm -rf "$dst"
  return 0
}

fallback_clone_local_repo() {
  local dst="$1"
  shift
  local candidates=("$@")
  for src in "${candidates[@]}"; do
    if [[ ! -d "$src/.git" ]]; then
      continue
    fi

    if ! prepare_clone_destination "$dst"; then
      return 1
    fi

    echo "[bootstrap] fallback: cloning local repo $src -> $dst"
    if git clone --quiet "$src" "$dst"; then
      return 0
    fi
  done
  return 1
}

echo "[bootstrap] syncing and initializing submodules..."
git submodule sync --recursive
if ! git submodule update --init --recursive; then
  echo "[bootstrap] submodule update failed, trying local fallback mirrors..."
fi

WORK_ROOT="$(cd "$ROOT/.." && pwd)"
CODX_DST="$ROOT/LAM_Test/agents/codex-agent"
COMM_DST="$ROOT/LAM_Test/agents/comm-agent"
OPER_DST="$ROOT/LAM_Test/agents/operator-agent"

if [[ ! -d "$CODX_DST/src" ]]; then
  fallback_clone_local_repo "$CODX_DST" \
    "$WORK_ROOT/LAM-Codex_Agent" \
    "$WORK_ROOT/LAM_Codex_Agent" || true
fi
if [[ ! -d "$COMM_DST/src" ]]; then
  fallback_clone_local_repo "$COMM_DST" \
    "$WORK_ROOT/LAM_Comunication_Agent" \
    "$WORK_ROOT/LAM_Communication_Agent" || true
fi
if [[ ! -d "$OPER_DST/agent" ]]; then
  fallback_clone_local_repo "$OPER_DST" \
    "$WORK_ROOT/Operator_Agent" || true
fi

required=(
  "$ROOT/LAM_Test/agents/codex-agent/src"
  "$ROOT/LAM_Test/agents/comm-agent/src"
  "$ROOT/LAM_Test/agents/operator-agent/agent"
)

missing=0
for p in "${required[@]}"; do
  if [[ ! -d "$p" ]]; then
    echo "[bootstrap] missing: $p"
    missing=1
  fi
done

if (( missing )); then
  echo "[bootstrap] FAILED: required submodule source paths are missing"
  exit 1
fi

echo "[bootstrap] OK: submodules ready"
