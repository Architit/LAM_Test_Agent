# GLOBAL REALTIME CIRCULATION PROTOCOL V1

## Purpose
Define global synchronization and realtime data circulation with dedicated inversion flow for test-report intelligence.

## Streams
1. Forward circulation:
- Local gateway state -> shared cloud mirror (`sync-gdrive`).
- Covers operational data exchange and policy-controlled payloads.

2. Reverse circulation (inversion):
- Shared cloud mirror -> local gateway (`sync-from-gdrive`).
- Dedicated for test-report return flow and cross-node verification signals.

## Inversion Test-Report Flow
- Producer node exports bundle into:
  - `.gateway/circulation/inversion/outbox/<node_id>/report_<timestamp>.json`
- Bundle includes:
  - latest microtick summaries
  - tail of background test failures
- Consumer node ingests foreign bundles into:
  - `.gateway/circulation/inversion/inbox/<producer>/...`
- Deduplication:
  - SHA256 registry in `.gateway/circulation/inversion/seen_sha256.tsv`
- Audit index:
  - `.gateway/circulation/inversion/index.jsonl`
- Cryptographic mirror (integrity/authenticity):
  - sidecar signature: `report_<ts>.json.sig.json`
  - fields: `sha256`, `hmac_sha256`, `key_id`
  - verify on ingest with dual key support:
    - primary key (active signer)
    - secondary key (grace-period verifier during rotation)
  - reject on mismatch/expired grace in required mode

## Runtime Service
- `scripts/lam_realtime_circulation.sh --daemon`
- `scripts/lam_hmac_rotation_daemon.sh --daemon`
- Default interval: 12 sec (`LAM_CIRCULATION_INTERVAL_SEC`)
- Integrated into bridge stack as `realtime_circulation` process.

## Required Policy Controls
- Circulation policy sync on stack start.
- Class/provider/org allowlist enforcement in gateway policy.
- Emergency kill-switch for circulation:
  - `scripts/lam_gateway.sh circulation-kill-switch on|off|status`

## Reliability Rules
- Sync failures are non-fatal for daemon loop; retries continue next cycle.
- Ingestion is idempotent by SHA deduplication.
- All ingested inversion reports are indexed for audit and replay.
- Crypto verify failures are indexed with `inversion_report_rejected_crypto`.

## Operational Commands
```bash
scripts/lam_realtime_circulation.sh --once
scripts/lam_realtime_circulation.sh --daemon --interval-sec 12
scripts/lam_realtime_circulation.sh --status
scripts/lam_bridge_stack.sh status
```

## Security Notes
- No credential material is stored in repo payloads.
- Data circulation boundaries remain governed by `routing_policy.json` (`data_circulation` section).
- Sensitive/restricted classes require contract and approval references.
- Crypto mirror controls:
  - `LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR=1|0`
  - primary key: `LAM_CIRCULATION_HMAC_KEY` or `LAM_CIRCULATION_HMAC_KEY_FILE`
  - secondary key: `LAM_CIRCULATION_HMAC_SECONDARY_KEY` or `LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE`
  - rotation state: `LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE`
  - grace window:
    - `LAM_CIRCULATION_HMAC_SECONDARY_GRACE_SEC`
    - or explicit deadline `LAM_CIRCULATION_HMAC_SECONDARY_VALID_UNTIL_EPOCH`
  - fallback key source: `LAM_HUB_ROOT/rootkey_expected_sha256.txt`
  - `LAM_CIRCULATION_HMAC_KEY_ID`
