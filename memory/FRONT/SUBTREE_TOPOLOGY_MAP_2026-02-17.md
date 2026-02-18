# SUBTREE TOPOLOGY MAP
Date: 2026-02-17
Profile: semantic-selection-v2 + trinity-golden-v1

## Canonical Path Pattern
`<system_id>/<call_sign>/<artifact_group>/`

## Artifact Groups
- protocols
- contracts
- policies
- atlas
- maps
- chronologs
- logs
- journals
- matrices

## Canonical File Mapping
- `PROTOCOLS_LIST_*.txt` -> `protocols/`
- `CONTRACTS_LIST_*.txt` -> `contracts/`
- `POLICIES_LIST_*.txt` -> `policies/`
- `ATLAS_LIST_*.txt` -> `atlas/`
- `MAPS_LIST_*.txt` -> `maps/`
- `CHRONOLOGS_LIST_*.txt` -> `chronologs/`
- `LOGS_LIST_*.txt` -> `logs/`
- `JOURNALS_LIST_*.txt` -> `journals/`
- `MATRICES_LIST_*.txt` -> `matrices/`

## Priority Entities (Pilot)
1. `LRPT/Larpat`
2. `TSPT/Taspit`

## Validation Rules
1. Every promoted subtree path must have triplet metadata from `SEMANTIC_IDENTITY_MAP`.
2. Any `HOLD` identity is blocked from promotion.
3. Count/hash parity between source memory and subtree target is mandatory.
4. No overwrite without checkpoint in `GUARD_HEAL` layer.

## Wave Blueprint
- Wave P0: topology + dry-run path checks.
- Wave P1: pilot (`LRPT/Larpat`, `TSPT/Taspit`).
- Wave P2+: repo batches with stop/go gates.
