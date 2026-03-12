#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:-text}"

echo "[provider-ready-gate] verify"
bash scripts/provider_mesh_bootstrap.sh verify >/dev/null

echo "[provider-ready-gate] apply"
bash scripts/provider_mesh_bootstrap.sh apply >/dev/null

echo "[provider-ready-gate] run external provider mesh"
MESH_JSON="$(bash scripts/lam_external_provider_mesh.sh --once)"

echo "[provider-ready-gate] run feedback gateway"
FEEDBACK_JSON="$(bash scripts/lam_feedback_gateway.sh --once)"

echo "[provider-ready-gate] run gws bridge"
GWS_JSON="$(bash scripts/lam_gws_bridge.sh --once)"

python3 - <<'PY' "$MESH_JSON" "$FEEDBACK_JSON" "$GWS_JSON" "$MODE"
import json
import sys

mesh = json.loads(sys.argv[1])
feedback = json.loads(sys.argv[2])
gws = json.loads(sys.argv[3])
mode = sys.argv[4]

providers = mesh.get("providers", [])
not_ready = [p.get("name", "unknown") for p in providers if not p.get("ready")]

summary = {
    "providers_ready": mesh.get("providers_ready", 0),
    "providers_total": mesh.get("providers_total", 0),
    "status": mesh.get("signals", {}).get("status", "unknown"),
    "not_ready": not_ready,
    "feedback_status": feedback.get("signals", {}).get("status", "unknown"),
    "feedback_ready_channels": feedback.get("ready_channels", []),
    "gws_overall_ok": gws.get("health", {}).get("overall_ok", False),
}

if mode == "--json":
    print(json.dumps(summary, ensure_ascii=True))
else:
    print("[provider-ready-gate] summary")
    print(f"providers_ready={summary['providers_ready']}/{summary['providers_total']}")
    print(f"status={summary['status']}")
    print(f"not_ready={','.join(summary['not_ready']) if summary['not_ready'] else 'none'}")
    print(f"feedback_status={summary['feedback_status']}")
    print(f"feedback_ready_channels={','.join(summary['feedback_ready_channels'])}")
    print(f"gws_overall_ok={summary['gws_overall_ok']}")
PY
