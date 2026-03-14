# AGENT CONTRACT TEMPLATE

## Metadata
- Contract ID:
- Version:
- Owner:
- Service/Agent Name:
- Effective Date:
- Review Interval:

## 1. Purpose
- Primary mission:
- Non-goals:

## 2. Authority Scope
- Allowed actions:
- Forbidden actions:
- Required explicit approvals:

## 3. Interfaces
- Inputs:
- Outputs:
- Upstream dependencies:
- Downstream dependencies:

## 4. Safety and Security Gates
- Preflight checks:
  - Licensing compliance gate (`scripts/license_audit_scan.sh`) with zero blocking findings.
  - Fail-safe governance contract check (`infra/governance/FAILSAFE_GOVERNANCE_CONTRACT_V1.md`) acknowledged.
- Runtime security checks:
- Rollback/revoke path:
- Lockdown behavior:

## 5. SLO/SLA
- Availability target:
- Max response latency:
- Recovery objectives (RTO/RPO):

## 6. Risk Classification
- Risk class (P1/P2/P3):
- Blast radius estimate:
- Guardrails:

## 7. Escalation Path
- Primary on-call:
- Secondary on-call:
- Incident channel:
- Emergency override owner:

## 8. Telemetry and Audit
- Metrics emitted:
- Logs path:
- Mandatory audit events:
- Retention requirements:

## 9. Compliance and Data Policy
- Data classes handled:
- Allowed data destinations:
- Data minimization rules:
- Encryption requirements:

## 10. Acceptance Criteria
- Test evidence:
- Security review status:
- Deployment gate status:

## 11. Signature
- Operator:
- Security approver:
- Date:
