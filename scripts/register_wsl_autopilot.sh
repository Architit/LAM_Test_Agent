#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_NAME="${1:-LAM_WSL_Autopilot}"

if ! grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  echo "[wsl-autopilot] this helper is intended for WSL." >&2
  exit 2
fi

if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "[wsl-autopilot] powershell.exe not found in WSL PATH." >&2
  exit 1
fi

WIN_REPO="$(wslpath -w "$ROOT")"
powershell.exe -ExecutionPolicy Bypass -File "$(wslpath -w "$ROOT/scripts/windows/register_wsl_autopilot.ps1")" -RepoPath "$WIN_REPO" -TaskName "$TASK_NAME"

echo "[wsl-autopilot] done"
