#!/usr/bin/env bash
set -euo pipefail

# DevKit patch helper with Phase B runtime guardrails.
#
# Usage:
#   cat change.patch | devkit/patch.sh --sha256 <64hex> --task-id <id> --spec-file <path>

usage() {
  cat <<'USAGE'
DevKit patch helper.

Usage:
  cat change.patch | devkit/patch.sh --sha256 <64hex> --task-id <id> --spec-file <path>
  devkit/patch.sh --file <path> --sha256 <64hex> --task-id <id> --spec-file <path>

Reads a unified diff, verifies artifact integrity, applies it via git in a reproducible way,
and stages the result.

Options:
  -h, --help            Show this help and exit.
  --file <path>         Read patch from file instead of stdin.
  --sha256 <64hex>      Expected SHA-256 for patch artifact (required).
  --task-id <id>        Task identifier for audit chain (required).
  --spec-file <path>    Task spec file for non-empty spec_hash (required).
USAGE
}

PATCH_INPUT_FILE=""
PATCH_SHA256=""
TASK_ID=""
SPEC_FILE=""
SPEC_HASH=""
ARTIFACT_HASH=""
COMMIT_REF="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

emit_status() {
  local status="$1"
  local error_code="${2:-NONE}"
  echo "status=$status"
  echo "error_code=$error_code"
}

emit_trace() {
  local apply_result="$1"
  echo "trace: task_id=$TASK_ID spec_hash=$SPEC_HASH artifact_hash=$ARTIFACT_HASH apply_result=$apply_result commit_ref=$COMMIT_REF"
}

die_status() {
  local status="$1"
  local error_code="$2"
  local message="$3"
  local apply_result="${4:-$status}"
  emit_status "$status" "$error_code"
  echo "message=$message"
  emit_trace "$apply_result"
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --file)
      shift
      PATCH_INPUT_FILE="${1:-}"
      if [ -z "$PATCH_INPUT_FILE" ]; then
        echo "ERROR: --file requires a path argument" >&2
        echo >&2
        usage >&2
        exit 2
      fi
      ;;
    --sha256)
      shift
      PATCH_SHA256="${1:-}"
      if [ -z "$PATCH_SHA256" ]; then
        echo "ERROR: --sha256 requires a hex digest argument" >&2
        exit 2
      fi
      ;;
    --task-id)
      shift
      TASK_ID="${1:-}"
      if [ -z "$TASK_ID" ]; then
        echo "ERROR: --task-id requires a value" >&2
        exit 2
      fi
      ;;
    --spec-file)
      shift
      SPEC_FILE="${1:-}"
      if [ -z "$SPEC_FILE" ]; then
        echo "ERROR: --spec-file requires a path argument" >&2
        exit 2
      fi
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      echo >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
 done

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found in PATH" >&2
  exit 2
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die_status "precondition_failed" "PATCH_NOT_IN_GIT_WORKTREE" "not inside a git repository"
fi

if [ -z "$PATCH_SHA256" ]; then
  die_status "precondition_failed" "PATCH_SHA256_REQUIRED" "missing_patch_sha256"
fi
if ! [[ "$PATCH_SHA256" =~ ^[0-9a-fA-F]{64}$ ]]; then
  die_status "precondition_failed" "PATCH_SHA256_FORMAT_INVALID" "invalid_patch_sha256 expected_64_hex"
fi
if [ -z "$TASK_ID" ]; then
  die_status "precondition_failed" "PATCH_TASK_ID_REQUIRED" "missing_task_id"
fi
if [ -z "$SPEC_FILE" ]; then
  die_status "precondition_failed" "PATCH_SPEC_FILE_REQUIRED" "missing_spec_file"
fi
if [ ! -r "$SPEC_FILE" ] || [ -d "$SPEC_FILE" ]; then
  die_status "precondition_failed" "PATCH_SPEC_NOT_READABLE" "unreadable_spec_file path=$SPEC_FILE"
fi
if ! command -v sha256sum >/dev/null 2>&1; then
  die_status "precondition_failed" "PATCH_SHA256_TOOL_UNAVAILABLE" "missing_sha256sum"
fi

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  die_status "precondition_failed" "PATCH_TREE_NOT_CLEAN" "working tree/index must be clean before patch apply"
fi

PATCH_FILE="$(mktemp)"
trap 'rm -f "$PATCH_FILE"' EXIT

if [ -n "$PATCH_INPUT_FILE" ]; then
  if [ ! -r "$PATCH_INPUT_FILE" ] || [ -d "$PATCH_INPUT_FILE" ]; then
    die_status "precondition_failed" "PATCH_INPUT_NOT_READABLE" "patch file not readable: $PATCH_INPUT_FILE"
  fi
  if [ ! -s "$PATCH_INPUT_FILE" ]; then
    die_status "precondition_failed" "PATCH_INPUT_EMPTY" "empty patch input"
  fi
  cat -- "$PATCH_INPUT_FILE" > "$PATCH_FILE"
else
  if [ -t 0 ]; then
    die_status "precondition_failed" "PATCH_INPUT_MISSING" "no patch provided on stdin"
  fi

  if ! IFS= read -r -n 1 first_char; then
    die_status "precondition_failed" "PATCH_INPUT_EMPTY" "empty patch input"
  fi
  printf %s "$first_char" > "$PATCH_FILE"
  cat >> "$PATCH_FILE"

  if [ ! -s "$PATCH_FILE" ]; then
    die_status "precondition_failed" "PATCH_INPUT_EMPTY" "empty patch input"
  fi
fi

SPEC_HASH="$(sha256sum "$SPEC_FILE" | awk '{print $1}')"
if [ -z "$SPEC_HASH" ]; then
  die_status "precondition_failed" "PATCH_SPEC_HASH_EMPTY" "empty_spec_hash"
fi

ARTIFACT_HASH="$(sha256sum "$PATCH_FILE" | awk '{print $1}')"
if [ "$ARTIFACT_HASH" != "$PATCH_SHA256" ]; then
  emit_status "integrity_mismatch" "PATCH_SHA256_MISMATCH"
  echo "expected_sha256=$PATCH_SHA256"
  echo "actual_sha256=$ARTIFACT_HASH"
  emit_trace "integrity_mismatch"
  exit 1
fi

if ! git apply --check --3way "$PATCH_FILE" >/dev/null 2>&1; then
  emit_status "conflict_detected" "PATCH_CONFLICT_DETECTED"
  emit_trace "conflict_detected"
  exit 1
fi

git apply --index --3way "$PATCH_FILE"
emit_status "success" "NONE"
emit_trace "success"
git --no-pager diff --cached --stat
