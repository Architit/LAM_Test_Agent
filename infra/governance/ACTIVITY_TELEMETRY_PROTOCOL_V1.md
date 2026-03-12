# ACTIVITY TELEMETRY PROTOCOL V1

## Purpose
Extended activity telemetry from runtime, archives, and database footprints.

## Sources
- bridge events/commands
- routing events
- runtime logs
- background test errors
- archive trees (`memory/ARCHIVE`, `data/local/ARCHIVE_SHADOWS`, `chronolog`, `journal`)
- local db footprints (`*.db`, `*.sqlite`, `*.sqlite3`)

## Runtime
- daemon: `scripts/lam_activity_telemetry.sh --interval-sec 20`
- one-shot scan: `scripts/lam_activity_telemetry.sh --once`

## State Outputs
- `LAM_HUB_ROOT/activity_telemetry_state.json`
- `LAM_HUB_ROOT/activity_telemetry_timeline.jsonl`
- audit appends into `LAM_HUB_ROOT/security_audit_stream.jsonl`

## Signals
- activity windows (5m / 60m)
- archive bytes/files totals
- db count/bytes totals
- staleness metrics for key streams
