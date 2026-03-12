# Device Gateways (Android / iOS / Watches / Earbuds)

This layer provides mobile/device mobility for the Captain Bridge.

## Components
- Device registry in bridge state:
  - `.gateway/bridge/captain/devices.json`
- Device outbox queues:
  - `.gateway/bridge/captain/device_outbox/<device_id>.jsonl`
- Portal gateway API:
  - `GET /api/devices`
  - `POST /api/device/send`
  - `POST /api/command`

## Console Commands
- `register-device <id> <type> <platform> [endpoint]`
- `list-devices`
- `send-device <id> <message>`
- `bridge-status`
- `scripts/device_meshctl.sh pair/grant/revoke/list/sync-once`
- `scripts/device_meshctl.sh pair-profile ...`
- `scripts/device_meshctl.sh promote-full-access <id>`

## Onboarding
```bash
scripts/mobile_onboard.sh device_phone_1 phone android
scripts/mobile_onboard.sh device_phone_2 phone ios
scripts/mobile_onboard.sh device_watch_1 watch wearos
scripts/mobile_onboard.sh device_audio_1 earbuds earbuds
```

## Suggested Client Paths
- Android:
  - Tasker/Termux/own app polls `/api/status` and `/api/devices`, sends via `/api/device/send`.
- iOS:
  - Shortcuts/app wrapper calls portal APIs over local network/VPN.
- Watches/Earbuds:
  - register as endpoints; bridge routes short control messages via device outbox.

## Security Baseline
- Keep portal bound to private network.
- Use reverse proxy + token auth for internet exposure.
- Rotate onboarding tokens in `.gateway/bridge/captain/mobile_tokens`.
- Apply scope-based consent per device (no unrestricted global access mode).
- Trusted full-access mode is enabled only after verified/authenticated promotion.
