# OS DEV MAP

timestamp_utc: 2026-02-16T00:19:57Z
scope: local device execution substrate
mode: post-atplt md stabilization

## Substrate
- host: Windows + WSL2
- linux root: `/`
- windows drives mounted:
  - `C:\\ -> /mnt/c`
  - `A:\\ -> /mnt/a`
  - `B:\\ -> /mnt/b`

## Dev Zones
- SoT zone: `/home/architit/work/RADRILONIUMA-PROJECT`
- ecosystem repos zone: `/home/architit/work/*`
- migrated-risk zone: `/home/architit/repos/windows-migrated-b-core/CORE` (non-canonical)

## Operational Rules
- contracts-first
- observability-first
- derivation-only
- no runtime logic changes by governance map updates

## ATPLT MD Control
- atplt_md_state: INACTIVE
- activation_scope: Phase 7.0 governance execution
- deactivation_condition: `phase70_status = COMPLETE`
- deactivation_status: MET
- status_source: `GOV_STATUS.md`
- startup_review_protocol: `ESS_MAP_SYNC_REVIEW_OS_ATPLT_MD_STARTUP_PROTOCOL.md`
- startup_review_latest_asr: `gov/asr/sessions/2026-02-16__ASR__ess-map-sync-review-os-atplt-md-startup-protocol.md`
- startup_decision_state: DENY_STARTUP (no new activation contract)
- continuation_wave_state: COMPLETE
