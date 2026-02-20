# EVIDENCE POLICY

policy_version: v2.0.0
policy_type: observability_evidence
status: ACTIVE
effective_utc: 2026-02-16T05:42:10Z

## Purpose
- Standardize evidence quality for all ecosystem decisions.
- Ensure every governance statement is reproducible and auditable.

## Evidence Classes
1) source_of_truth_artifact
- canonical docs and registries in repository (`*.md`, `*.yaml`).

2) deterministic_command_output
- reproducible read-only command outputs over local state.

3) state_pointer_evidence
- synchronized state links in `GOV_STATUS.md`, `WORKFLOW_SNAPSHOT_STATE.md`, `TASK_MAP.md`.

4) event_evidence
- ASR entries in `gov/asr/sessions/` indexed by `gov/asr/INDEX.md`.

## Minimum Evidence Bundle per Decision
- decision_id (or asr_id),
- timestamp_utc,
- at least one SoT artifact path,
- at least one deterministic verification path,
- ASR pointer for non-trivial changes.

## Evidence Quality Grades
- `E3_STRONG`: reproducible command output + SoT artifact + ASR.
- `E2_MODERATE`: SoT artifact + ASR, command output omitted.
- `E1_WEAK`: narrative without reproducible anchor.
- `E0_INVALID`: unverifiable or contradictory claim.

## Acceptance Rules
- Operational decisions (`gate/open/block/allow/deny`) require `E3_STRONG`.
- Policy documentation-only changes require at least `E2_MODERATE`.
- `E1_WEAK` and `E0_INVALID` must not be used as closure evidence.

## Reproducibility Rules
- Time-sensitive claims must include explicit UTC timestamps.
- Every claim should map to stable file paths.
- Missing evidence must be marked as `insufficient_evidence`.

## Invalid Evidence
- memory-only assumptions,
- inferred ownership without declared registry or explicit artifact statement,
- unverifiable remote claims not represented in local evidence surfaces,
- stale pointers to missing ASR or missing indexed records.

## Conflict Handling
- On conflicting evidence, choose newer timestamp only if both are at least `E2_MODERATE`.
- If conflict cannot be resolved deterministically, set decision state to `BLOCKED_PENDING_POLICY_DECISION`.
