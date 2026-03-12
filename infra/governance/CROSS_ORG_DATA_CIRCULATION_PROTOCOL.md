# CROSS-ORG DATA CIRCULATION PROTOCOL V0.1

## Scope
Controlled data circulation across operator-owned organizational accounts and platforms, including OpenAI, Google, and Microsoft integrations.

## Security Principles
- Explicit consent and credential ownership by operator.
- Least privilege scopes only.
- Data minimization by class and destination.
- Immutable audit trail for every cross-org transfer.
- Default deny for unknown targets/scopes.

## Allowed Flow Model
1. Data classified (`public`, `internal`, `sensitive`, `restricted`).
2. Destination policy checked against class.
3. Contract + authority validated.
4. Transfer executed via approved gateway connector.
5. Result and hashes logged into audit stream.

## Prohibited
- Silent background transfer of `sensitive`/`restricted` data without explicit policy approval.
- Credential sharing between unrelated agents.
- Bypassing gateway policy through ad-hoc scripts.
- Cross-tenant writes when account ownership is unverified.

## Connector Requirements
- Token storage in secure secret store (no plaintext in repo).
- Per-provider scoped credentials:
  - OpenAI: API scopes limited to required endpoints.
  - Google: Workspace/Drive scopes minimal and explicit.
  - Microsoft: Graph/OneDrive scopes minimal and explicit.
- Token rotation and expiry checks.
- Health-check and circuit breaker support.

## Governance Gates
- Preflight gate: policy, scope, destination ownership.
- Runtime gate: throughput limits, anomaly detection, kill-switch.
- Post gate: checksum verification and reconciliation report.

## Audit Event Schema (minimum)
- `event_time`
- `contract_id`
- `agent_id`
- `data_class`
- `source_system`
- `destination_system`
- `object_ref`
- `checksum_sha256`
- `result_status`
- `operator_approval_ref`

## Incident Handling
- On unauthorized transfer attempt:
  1. Block transfer.
  2. Trigger P1/P2 according to data class.
  3. Preserve forensic logs.
  4. Require security sign-off before restore.

## Deployment Notes
- Implement as gateway policy layer; do not embed credentials in agent logic.
- Start with `internal` class only, then expand to higher classes after audit pass.
