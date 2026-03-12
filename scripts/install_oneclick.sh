#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  echo "[install-oneclick] WSL detected. Running bridge stack mode."
  cd "$ROOT"
  scripts/lam_bridge_stack.sh start
  echo "[install-oneclick] start Captain Bridge with: scripts/lam_console.sh"
  exit 0
fi

if [[ "$(uname -s)" == "Linux" ]]; then
  echo "[install-oneclick] Native Linux detected. Running autonomous bootstrap."
  cd "$ROOT"
  sudo scripts/autonomous_bootstrap.sh full --install-deps
  echo "[install-oneclick] done"
  exit 0
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "[install-oneclick] macOS detected. Running local bridge stack mode."
  cd "$ROOT"
  scripts/lam_bridge_stack.sh start
  echo "[install-oneclick] start Captain Bridge with: scripts/lam_console.sh"
  exit 0
fi

echo "[install-oneclick] Unsupported OS for autonomous install. Use native Linux target."
exit 2

