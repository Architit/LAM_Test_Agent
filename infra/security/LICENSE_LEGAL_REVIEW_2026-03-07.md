# License Legal Review 2026-03-07

Status: operational hardening review completed.
Scope: internal repositories, GitHub distribution surface, license update/change control.

## Executive Summary
- Ecosystem coverage is now clean on baseline checks: 36/36 repositories have recognized licenses.
- Current portfolio mix:
  - AGPL-3.0: 33 repos
  - MIT: 3 repos
- Non-GitHub remote warnings: 0.
- Main residual legal risk is not missing licenses anymore, but uncontrolled future relicensing.

## Key Legal-Operational Findings
1. License presence and type:
   - No missing `LICENSE` files in current scan.
   - No unknown license types.
2. Mixed-license ecosystem:
   - AGPL and MIT coexist. This is allowed, but integration/distribution paths must respect copyleft obligations where AGPL-covered components are involved.
3. Update mutability risk:
   - License text/type can be changed in future commits. Without change-control, this creates legal drift risk.
4. External publishing risk:
   - Public GitHub remotes mean licensing commitments are externally visible and time-stamped; accidental relicensing can create compliance incidents quickly.

## Can Licenses Be Changed?
Yes, for future versions when rights holders have authority.  
No, already-distributed versions generally retain the rights previously granted under their original license terms.  
If multiple contributors hold rights, relicensing requires sufficient rights/consent coverage.

## Control Enhancements Enforced
1. Baseline snapshot created:
   - `infra/governance/LICENSE_BASELINE.json`
2. Approval registry created:
   - `infra/governance/LICENSE_CHANGE_APPROVALS.json`
3. Change-control guard introduced:
   - `scripts/license_change_guard.sh --mode verify`
   - Blocks unapproved license hash/type changes.
4. Process integration:
   - `scripts/test_entrypoint.sh --license-audit`
   - `scripts/test_entrypoint.sh --license-baseline`
   - `scripts/test_entrypoint.sh --license-verify`

## Mandatory Approval Payload for Relicensing
Each approved license change must include:
- `repo_name`
- `license_sha256` (new license hash)
- `approved=true`
- `approval_id`
- `approved_by`
- `justification`
- `ts_utc`

## Recommended Ongoing Cadence
- Session start: run `--license-audit`
- Pre-merge/release: run `--license-verify`
- After any legitimate relicensing: update approvals registry and refresh baseline
