# AMBIENT LIGHT PER-KEY FEEDBACK PROTOCOL v1

## Purpose
Enable granular, per-LED or per-key RGB control for external devices (keyboards, mice, light strips) to provide direct user feedback (e.g., status, alerts, training, activity visualization).

## Sources
- Feedback producer: `apps/lam_console/feedback_engine.py` (New)
- Vector state: `.gateway/bridge/captain/ambient_light_grid.json`
- Vector stream: `.gateway/bridge/captain/ambient_light_grids.jsonl`
- Dispatcher: `apps/lam_console/ambient_light_daemon.py`

## Grid Schema
The `grid` field in the vector payload defines the mapping:
```json
{
  "op": "ambient_light_apply",
  "profile": "per_key_feedback",
  "vector": {
    "rgb": [40, 40, 40],
    "brightness_pct": 100,
    "grid": {
      "key_escape": [255, 0, 0],
      "key_enter": [0, 255, 0],
      "key_space": [0, 0, 255],
      "zone_logo": [255, 255, 0]
    },
    "mask": ["key_escape", "key_enter"]
  }
}
```

## Key Identifiers
- `key_<name>`: Standard key names (e.g., `key_a`, `key_1`, `key_ctrl_left`).
- `led_<index>`: Linear LED index for strips or non-keyboard devices.
- `zone_<name>`: Logical zones (e.g., `zone_numpad`, `zone_wasd`).

## Runtime Controls
- `LAM_AMBIENT_GRID_ENABLED=1|0`
- `LAM_AMBIENT_GRID_PRIORITY`: `0..255` (Override baseline ambient)

## Integration
Devices supporting this protocol must parse the `grid` field and map it to their internal LED addresses using a local mapping table.
