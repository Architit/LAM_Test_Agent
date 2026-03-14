# DATA RETENTION AND SECURE ERASURE POLICY

policy_version: v2.0.0
mode: lifeflowstream
security_model: zero trust
scope: local internal systems and mirrored governance surfaces
effective_utc: 2026-02-16T05:42:10Z

## Purpose
- Define deterministic retention and secure erasure controls.
- Prevent unauthorized destructive actions while preserving auditability.

## Data Classification
- `R1_CRITICAL`: identity, auth, keys, legal/audit artifacts.
- `R2_OPERATIONAL`: telemetry, workflow states, execution metrics.
- `R3_TEMPORARY`: transient processing artifacts and disposable cache outputs.

## Retention Rules
- R1: longest retention window, mandatory integrity and access controls.
- R2: bounded operational window based on observability needs.
- R3: shortest window, removable only through approved lifecycle process.

## Erasure Preconditions (all mandatory)
1) declared legal/compliance basis,
2) data owner approval,
3) security approval for sensitive classes,
4) evidence snapshot where required by policy,
5) ASR registration before execution.

## Erasure Decision States
- `ALLOW_ERASURE`: all preconditions satisfied.
- `ALLOW_WITH_REVIEW`: non-critical uncertainty exists.
- `DENY_ERASURE`: missing legal basis or missing approvals.
- `BLOCKED_PENDING_POLICY_DECISION`: conflicting requirements.

## Secure Erasure Procedure
1. Identify dataset and classification (`R1/R2/R3`).
2. Freeze active writes and revoke access references.
3. Execute storage-specific secure erase method.
4. Verify deletion/non-recoverability where technically feasible.
5. Record post-check evidence and ASR linkage.

## Safety Controls
- No unattended destructive wipe triggered by unverified signals.
- Two-person approval for high-impact erasure.
- MFA required for approval and execution roles.
- Post-erasure verification report is mandatory for closure.

## Audit Requirements
- Every erasure operation must include:
  - dataset identifier,
  - classification,
  - approver IDs/roles,
  - execution timestamp,
  - verification evidence pointer.
