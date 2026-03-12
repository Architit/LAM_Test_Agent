# IO Spectral Analysis Protocol V1

## Purpose
Vector spectral analysis of input/output frequency and response behavior for:
- buttons/keys/touch
- sensors/scanners
- components/modules/core zones
- interaction surfaces/spaces

## Runtime
- daemon: `scripts/lam_io_spectral.sh --interval-sec 12`
- one-shot: `scripts/lam_io_spectral.sh --once`

## Inputs
- `.gateway/bridge/captain/events.jsonl`
- `.gateway/bridge/captain/commands.jsonl`

## Outputs
- state: `LAM_HUB_ROOT/io_spectral_state.json`
- timeline: `LAM_HUB_ROOT/io_spectral_timeline.jsonl`
- audit stream event: `source=io_spectral`, `event=io_spectral_snapshot`

## Spectral Bands
- `ultra_low_0_0_5hz`
- `low_0_5_2hz`
- `mid_2_8hz`
- `high_8_32hz`
- `ultra_high_32hz_plus`

## Signals
- `spectral_pressure`
- `dominant_domain`
- `io_event_count_window`
- latency profile (`p50_ms`, `p95_ms`, `max_ms`)
