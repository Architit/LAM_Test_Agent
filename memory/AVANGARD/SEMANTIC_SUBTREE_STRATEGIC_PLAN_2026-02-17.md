# SEMANTIC SUBTREE STRATEGIC PLAN
Date: 2026-02-17
Mode: ecosystem-wide, contracts-first

## Mission
Migrate all collected list artifacts into git subtree topology with semantic-selection identity naming by canonical triplet:
- true_name
- call_sign
- system_id

Reference identities:
- Loarachspoiszat / Larpat / LRPT
- Tendshpoisat / Taspit / TSPT

## Scope of Artifacts
- PROTOCOLS_LIST
- CONTRACTS_LIST
- POLICIES_LIST
- ATLAS_LIST
- MAPS_LIST
- CHRONOLOGS_LIST
- LOGS_LIST
- JOURNALS_LIST
- MATRICES_LIST

## Global Constraints
- contracts-first
- observability-first
- derivation-only
- no destructive rewrite without recovery checkpoint
- no silent naming drift

## Phase Plan

### Phase 0: Governance Lock
Actions:
1. Freeze list schema and naming suffix (`*_LIST_YYYY-MM-DD.txt`).
2. Freeze canonical source roots (`repo/memory/*`).
3. Register migration session id in DEV_LOGS and WORKFLOW_SNAPSHOT.
Done criteria:
- schema locked
- source paths locked
- session tag recorded

### Phase 1: Semantic Identity Matrix
Actions:
1. Build `SEMANTIC_IDENTITY_MAP.tsv` with columns:
   `repo,true_name,call_sign,system_id,subtree_prefix`.
2. Validate triplet uniqueness by `system_id`.
3. Mark unresolved entities as `HOLD`.
Done criteria:
- matrix complete
- collisions = 0
- holds explicitly listed

### Phase 2: Subtree Topology Blueprint
Actions:
1. Define target subtree path pattern:
   `<system_id>/<call_sign>/<artifact_group>/`.
2. Define artifact groups:
   `protocols,contracts,policies,atlas,maps,chronologs,logs,journals,matrices`.
3. Publish `SUBTREE_TOPOLOGY_MAP.md`.
Done criteria:
- topology approved
- path pattern immutable for this wave

### Phase 3: Pilot Wave (Larpat + Taspit)
Actions:
1. Execute subtree migration for LRPT and TSPT only.
2. Copy all 9 artifact families.
3. Verify checksums source vs target.
Done criteria:
- 100% file parity
- 0 checksum mismatch
- pilot sign-off recorded

### Phase 4: Main Rollout Waves
Actions:
1. Roll out by batches (3-5 repos/wave).
2. Per wave run:
   - preflight
   - subtree sync
   - artifact copy
   - validation
   - checkpoint write
3. On failure: wave `HOLD`, no partial promotion.
Done criteria:
- all repos processed
- all waves have checkpoint records

### Phase 5: Guard-Heal and Recovery
Actions:
1. Persist recovery packs before each wave:
   - status snapshot
   - file manifest
   - rollback pointers
2. Keep guard rules:
   - forbid overwrite without backup
   - forbid unresolved triplet promotion
3. Heal protocol on error:
   - restore from checkpoint
   - replay with narrowed scope
Done criteria:
- every wave recoverable
- zero unrecoverable state

### Phase 6: Archive and Frontline Synchronization
Actions:
1. Write frontline state (`FRONT`) for active execution.
2. Write vanguard state (`AVANGARD`) for next-wave actions.
3. Write archive state (`ARCHIVE`) for immutable history.
4. Write guard-heal state (`GUARD_HEAL`) for rollback and incident flow.
Done criteria:
- all four layers updated per wave
- timestamps and session ids aligned

## Operational Checklists

### Preflight Checklist
- canonical source exists
- triplet present
- subtree prefix valid
- memory layer writable
- recovery folder writable

### Postflight Checklist
- file count parity
- checksum parity
- naming conformity
- session trace in DEV_LOGS
- snapshot pointer updated

## Naming Compliance Rules
1. Every migrated unit MUST carry triplet metadata.
2. `system_id` is immutable per entity.
3. `call_sign` may evolve only with explicit migration note.
4. `true_name` change requires governance decision record.

## Risk Register
- R1: duplicate subtree roots
- R2: triplet collision
- R3: stale memory sources
- R4: partial wave completion
- R5: unsynced archive evidence

## Control Decisions
- On R1/R2: STOP + HOLD
- On R3: refresh source manifest then resume
- On R4: rollback wave and rerun
- On R5: archive sync mandatory before next wave

## Next Execution Command Pack
1. Build semantic identity map.
2. Build subtree topology map.
3. Run pilot wave for LRPT/TSPT.
4. Validate and publish wave checkpoint.
