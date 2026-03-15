#!/usr/bin/env bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# Run the executor once if triggered or on boot
if [ -f "$ROOT/scripts/agent_executor_daemon.py" ]; then
    python3 scripts/agent_executor_daemon.py
fi
