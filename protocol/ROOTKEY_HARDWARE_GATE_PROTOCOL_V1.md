# ROOTKEY HARDWARE GATE PROTOCOL V1

## Purpose
Authorize high-privilege gateway initialization only when a paired physical removable key is actively connected.

## Primary Key Role
- `architit root` is the first initiation key.
- Activation path emits mode:
  - `SEED_GOD_MODE_SPREAD_FLOW_INIT`

## Runtime
- daemon: `scripts/lam_rootkey_gate.sh --interval-sec 5`
- one-shot: `scripts/lam_rootkey_gate.sh --once`

## Required Conditions
1. `LAM_ROOTKEY_ENABLE=1`
2. Paired approval present:
   - `LAM_HUB_ROOT/rootkey_pairing.json`
   - required fields: `enabled=true`, `owner=architit`, `key_id=<id>`
3. Active physical key file present on removable media:
   - `${LAM_ROOTKEY_MEDIA_ROOT}/${LAM_ROOTKEY_FILE_REL}`
4. Optional digest verification:
   - `LAM_ROOTKEY_ARCHITIT_SHA256=<sha256>`
   - or `LAM_HUB_ROOT/rootkey_expected_sha256.txt`
5. Security posture must be valid:
   - no `security_lockdown.flag`
6. One-time challenge-response (2FA):
   - challenge file: `LAM_HUB_ROOT/rootkey_challenge.json`
   - response file on removable media: `${LAM_ROOTKEY_MEDIA_ROOT}/${LAM_ROOTKEY_RESPONSE_FILE_REL}`
   - response formula: `sha256("<nonce>:<sha256(key_payload)>")`
   - challenge TTL: `LAM_ROOTKEY_CHALLENGE_TTL_SEC`
   - auto-rotation interval: `LAM_ROOTKEY_CHALLENGE_AUTO_ROTATE_SEC`
   - fail2ban threshold: `LAM_ROOTKEY_FAIL_THRESHOLD`
   - fail2ban window: `LAM_ROOTKEY_BAN_SEC`

## State
- `LAM_HUB_ROOT/rootkey_gate_state.json`
- `LAM_HUB_ROOT/rootkey_active.flag`
- `LAM_HUB_ROOT/seed_flow_init.flag`
- `LAM_HUB_ROOT/rootkey_challenge_counters.json`
- `LAM_HUB_ROOT/rootkey_challenge_ban.json`

## Guardrails
- If pairing or key validation fails, mode stays `inactive`.
- Under lockdown, activation is blocked regardless of key presence.
- Gate records events/audit stream on every cycle.

## Pairing Helper
- Pair: `scripts/rootkey_pair.sh pair --owner architit --key-id AK-001`
- Revoke: `scripts/rootkey_pair.sh revoke`
- Status: `scripts/rootkey_pair.sh status`

## Challenge Helper
- Issue challenge: `scripts/rootkey_challenge.sh issue --ttl-sec 180`
- Solve on active removable key: `scripts/rootkey_challenge.sh solve`
- Status: `scripts/rootkey_challenge.sh status`
- Clear: `scripts/rootkey_challenge.sh clear`
