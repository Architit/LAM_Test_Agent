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

submodule_recorded_commit() {
  local submodule_path="$1"
  local expected_sha
  expected_sha="$(git ls-tree HEAD -- "$submodule_path" 2>/dev/null | awk '{print $3}')"
  if [[ -z "$expected_sha" ]]; then
    return 1
  fi
  printf '%s\n' "$expected_sha"
}

pin_submodule_to_recorded_commit() {
  local submodule_path="$1"
  local dst="$2"
  if [[ ! -d "$dst/.git" ]]; then
    return 1
  fi

  local expected_sha current_sha
  expected_sha="$(submodule_recorded_commit "$submodule_path" || true)"
  if [[ -z "$expected_sha" ]]; then
    return 1
  fi

  current_sha="$(git -C "$dst" rev-parse HEAD 2>/dev/null || true)"
  if [[ "$current_sha" == "$expected_sha" ]]; then
    return 0
  fi

  if git -C "$dst" cat-file -e "${expected_sha}^{commit}" >/dev/null 2>&1; then
    echo "[bootstrap] pinning $submodule_path to recorded commit $expected_sha"
    git -C "$dst" checkout --quiet "$expected_sha" || true
    current_sha="$(git -C "$dst" rev-parse HEAD 2>/dev/null || true)"
    [[ "$current_sha" == "$expected_sha" ]]
    return
  fi

  echo "[bootstrap] WARN: recorded commit $expected_sha not found in $submodule_path clone; leaving current HEAD"
  return 1
}

ensure_submodule_recorded_commit() {
  local submodule_path="$1"
  local dst="$2"
  shift 2
  local candidates=("$@")
  local expected_sha current_sha src

  expected_sha="$(submodule_recorded_commit "$submodule_path" || true)"
  if [[ -z "$expected_sha" ]]; then
    return 0
  fi

  current_sha="$(git -C "$dst" rev-parse HEAD 2>/dev/null || true)"
  if [[ "$current_sha" == "$expected_sha" ]]; then
    return 0
  fi

  if pin_submodule_to_recorded_commit "$submodule_path" "$dst"; then
    return 0
  fi

  for src in "${candidates[@]}"; do
    if [[ ! -d "$src/.git" ]]; then
      continue
    fi
    if ! git -C "$src" cat-file -e "${expected_sha}^{commit}" >/dev/null 2>&1; then
      continue
    fi
    if fallback_clone_local_repo "$dst" "$src"; then
      if pin_submodule_to_recorded_commit "$submodule_path" "$dst"; then
        return 0
      fi
    fi
  done

  echo "[bootstrap] WARN: unable to align $submodule_path to recorded commit $expected_sha"
  return 0
}

echo "[bootstrap] syncing and initializing submodules..."
git submodule sync --recursive
if getent hosts github.com >/dev/null 2>&1; then
  if ! git submodule update --init --recursive; then
    echo "[bootstrap] submodule update failed, trying local fallback mirrors..."
  fi
else
  echo "[bootstrap] github.com not resolvable; skipping remote submodule update and using local fallbacks"
fi

resolve_work_root() {
  if [[ -n "${ECO_WORK_ROOT:-}" ]] && [[ -d "${ECO_WORK_ROOT:-}" ]]; then
    printf '%s\n' "$ECO_WORK_ROOT"
    return 0
  fi

  local candidate
  for candidate in \
    "$ROOT/../../.." \
    "$ROOT/../.." \
    "$ROOT/.." \
    "$(pwd)"; do
    if [[ -d "$candidate/LAM-Codex_Agent/.git" ]] && [[ -d "$candidate/LAM_Comunication_Agent/.git" ]]; then
      (cd "$candidate" && pwd)
      return 0
    fi
  done

  (cd "$ROOT/.." && pwd)
}

WORK_ROOT="$(resolve_work_root)"
echo "[bootstrap] using work root: $WORK_ROOT"
CODX_DST="$ROOT/LAM_Test/agents/codex-agent"
COMM_DST="$ROOT/LAM_Test/agents/comm-agent"
OPER_DST="$ROOT/LAM_Test/agents/operator-agent"

if [[ ! -d "$CODX_DST/src" ]]; then
  fallback_clone_local_repo "$CODX_DST" \
    "$WORK_ROOT/LAM_Test_Agent/LAM_Test/agents/codex-agent" \
    "$WORK_ROOT/LAM-Codex_Agent" \
    "$WORK_ROOT/LAM_Codex_Agent" || true
fi
if [[ ! -d "$COMM_DST/src" ]]; then
  fallback_clone_local_repo "$COMM_DST" \
    "$WORK_ROOT/LAM_Test_Agent/LAM_Test/agents/comm-agent" \
    "$WORK_ROOT/LAM_Comunication_Agent" \
    "$WORK_ROOT/LAM_Communication_Agent" || true
fi
if [[ ! -d "$OPER_DST/agent" ]]; then
  fallback_clone_local_repo "$OPER_DST" \
    "$WORK_ROOT/LAM_Test_Agent/LAM_Test/agents/operator-agent" \
    "$WORK_ROOT/Operator_Agent" || true
fi

ensure_submodule_recorded_commit "LAM_Test/agents/codex-agent" "$CODX_DST" \
  "$WORK_ROOT/LAM_Test_Agent/LAM_Test/agents/codex-agent" \
  "$WORK_ROOT/LAM-Codex_Agent" \
  "$WORK_ROOT/LAM_Codex_Agent"
ensure_submodule_recorded_commit "LAM_Test/agents/comm-agent" "$COMM_DST" \
  "$WORK_ROOT/LAM_Test_Agent/LAM_Test/agents/comm-agent" \
  "$WORK_ROOT/LAM_Comunication_Agent" \
  "$WORK_ROOT/LAM_Communication_Agent"
ensure_submodule_recorded_commit "LAM_Test/agents/operator-agent" "$OPER_DST" \
  "$WORK_ROOT/LAM_Test_Agent/LAM_Test/agents/operator-agent" \
  "$WORK_ROOT/Operator_Agent"

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
