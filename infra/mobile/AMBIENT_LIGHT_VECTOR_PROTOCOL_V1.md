# AMBIENT LIGHT VECTOR PROTOCOL v1

## Purpose
Mirror Interactionface zone activity to external device lighting (Aura-style ambient) through the local bridge bus.

## Sources
- UI producer: `apps/lam_console/app.py`
- Vector state: `.gateway/bridge/captain/ambient_light_vector.json`
- Vector stream: `.gateway/bridge/captain/ambient_light_vectors.jsonl`
- Dispatcher: `scripts/lam_ambient_light.sh` (`apps/lam_console/ambient_light_daemon.py`)

## Device Access Gate
Device must satisfy:
- `consent.approved == true`
- scope includes `ambient_light`

Alternative:
- `full_data_access` + `trust_level == verified_full`

## Dispatch Contract
Daemon writes to `.gateway/bridge/captain/device_outbox/<device_id>.jsonl`:
- `op`: `ambient_light_apply`
- `profile`: `aura_ambient_mirror`
- `mode`: `idle|inversion|surge`
- `pane`, `mirror_pane`
- `vector.rgb` (0..255)
- `vector.brightness_pct` (0..100)
- `vector.wave_hz`
- `vector.phase`: `aligned|anti`

## Runtime Controls
- `LAM_UI_AMBIENT_LIGHT_ENABLED=1|0`
- `LAM_UI_AMBIENT_LIGHT_INTERVAL_SEC` (UI publish rate)
- `LAM_UI_AMBIENT_LIGHT_MAX_BRIGHTNESS`
- `LAM_AMBIENT_LIGHT_INTERVAL_SEC` (daemon loop from stack)
- `LAM_AMBIENT_DISPATCH_MIN_INTERVAL_SEC` (per-device dedupe throttle)
