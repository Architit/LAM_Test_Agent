# MEDIA STREAM SYNC PROTOCOL V1

## Purpose
Realtime streaming synchronization between device storage and removable media with microtick-style isolation locks.

## Runtime
- daemon: `scripts/lam_media_sync.sh --interval-sec 6`
- one-shot: `scripts/lam_media_sync.sh --once`

## Modes
- `push` (device -> removable)
- `pull` (removable -> device)
- `bidirectional` (newer mtime wins)

## Priority Classes
Default class order:
1. `instructions`
2. `contracts`
3. `protocols`
4. `policies`
5. `licenses`
6. `map`
7. `cards`
8. `keypass_code_dnagen`
9. `other`

Per-tick class budgets are enforced before `other` traffic.

## Isolation Locking (Microtick Analogy)
- Active lock files: `.gateway/sync_zones/media_sync/active/*.lock`
- Lock ledger: `.gateway/sync_zones/media_sync/locks.tsv`
- Zone ledger: `.gateway/sync_zones/media_sync/zones.tsv`
- Tick logs: `.gateway/sync_zones/media_sync/ticks/tick_*.log`

Each file operation acquires/release lock in a microtick cycle.
If lock exists, operation is skipped for safety (`skipped_locked_ops`).

## State and Signals
- state: `LAM_HUB_ROOT/media_stream_sync_state.json`
- timeline: `LAM_HUB_ROOT/media_stream_sync_timeline.jsonl`
- signals:
  - `sync_pressure`
  - `lock_pressure`
  - `status` (`ok|degraded`)

## Environment
- `LAM_MEDIA_DEVICE_ROOT`
- `LAM_MEDIA_REMOVABLE_ROOT`
- `LAM_MEDIA_SYNC_MODE`
- `LAM_MEDIA_SYNC_INTERVAL_SEC`
- `LAM_MEDIA_SYNC_MAX_OPS_PER_TICK`
- `LAM_MEDIA_SYNC_MAX_SCAN_FILES`
- `LAM_MEDIA_SYNC_CLASS_ORDER`
- `LAM_MEDIA_SYNC_CLASS_MAX_OPS`
