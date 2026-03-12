# MULTIDEVICE MESH PROTOCOL V1

## Purpose
Enable cross-device workflow between laptop, phone, earbuds, pointer/mouse, and wearables via Wi-Fi/Bluetooth/Hybrid links with controlled data circulation.

## Supported Transports
- `wifi`
- `bluetooth`
- `hybrid` (wifi + bluetooth)
- `usb`

## Access Model
- Explicit pairing and consent required per device.
- Scope-based permissions only (no unrestricted global read/write mode).
- Mandatory audit trail for pair/grant/revoke/sync actions.
- Full data access is allowed only after:
  1. pairing + consent,
  2. verification and authentication success,
  3. promotion to trusted level (`verified_full`).

## Scopes
- `telemetry_read`
- `files_exchange`
- `audio_control`
- `input_control`
- `notifications`
- `device_status`
- `test_reports`
- `ambient_light`

## Control Commands
```bash
scripts/device_meshctl.sh pair <id> <type> <platform> <transport> <scopes_csv> --endpoint <url>
scripts/device_meshctl.sh pair-profile <windows_asus|windows_razer|samsung_android|google_android|earbuds_bluetooth|pointer_bluetooth|ambient_rgb> <id> --endpoint <url>
scripts/device_meshctl.sh grant <id> <scopes_csv>
scripts/device_meshctl.sh revoke <id>
scripts/device_meshctl.sh promote-full-access <id>
scripts/device_meshctl.sh list
scripts/device_meshctl.sh sync-once [all|device_id] [push|pull|bidirectional]
```

## Realtime Daemon
```bash
scripts/lam_device_mesh_daemon.sh --interval-sec 15 --direction bidirectional
scripts/lam_ambient_light.sh --interval-sec 2
```

State:
- Device registry: `.gateway/bridge/captain/devices.json`
- Mesh queue: `.gateway/bridge/captain/device_mesh_queue.jsonl`
- Device outbox: `.gateway/bridge/captain/device_outbox/<device_id>.jsonl`
- Daemon state: `LAM_HUB_ROOT/device_mesh_state.json`
- Ambient light vector state: `.gateway/bridge/captain/ambient_light_vector.json`
- Ambient dispatcher state: `LAM_HUB_ROOT/ambient_light_state.json`

## Vendor/Platform Analogy Map
- Windows / ASUS / Razer host workflows map to `laptop + pointer + audio` mesh roles.
- Samsung Android / Google Android phone workflows map to `phone + wearable` mesh roles.
- Protocol is vendor-agnostic at orchestration layer; capability depends on device-side adapters.

## Security
- Deny-by-default for unpaired devices.
- Revoke immediately clears scopes and disables sync dispatch.
- Sensitive data movement must remain under governance policy and circulation gates.
- `full_data_access` scope is ignored unless trust level is `verified_full`.
