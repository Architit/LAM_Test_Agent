# License Compliance Protocol V1

## Scope
Applies to all development agents and repositories discovered in the workspace ecosystem.

## Mandatory Licensing Gate
Before merge/release/global rollout, agent must pass licensing preflight:

```bash
scripts/license_audit_scan.sh
scripts/license_change_guard.sh --mode verify
```

Blocking conditions:
- missing `LICENSE`/`COPYING` file in any GitHub repository
- unknown license type without SPDX hint
- license text/type changed without explicit approval record in `infra/governance/LICENSE_CHANGE_APPROVALS.json`

Non-blocking warning:
- non-GitHub remote (must be explicitly documented by operator)

## Required Agent Behavior
1. Run licensing scan at session start and before final publish.
2. Run license change guard verify before merge/release.
3. Attach latest `LICENSE_AUDIT_REPORT_<date>.{json,md}` and guard output to governance evidence.
4. If blocked, stop release actions and provide remediation list by repository.
5. Do not auto-assign proprietary license text without explicit operator approval.

## License Update Legality (Control Rule)
- Yes, licenses can be changed for future versions by copyright holders.
- No, previously distributed versions do not lose rights already granted under earlier license terms.
- If there are multiple copyright contributors, relicensing needs rights coverage (assignment/CLA or explicit consent).
- Any relicensing must be tracked with approval artifact and repository-specific decision record.

## Change Control Workflow
1. Initialize baseline:
   - `scripts/license_change_guard.sh --mode snapshot`
2. On any future license edit:
   - add approval entry into `infra/governance/LICENSE_CHANGE_APPROVALS.json`
   - include fields: `repo_name`, `license_sha256`, `approved`, `approval_id`, `approved_by`, `justification`, `ts_utc`
3. Verify:
   - `scripts/license_change_guard.sh --mode verify`
4. Only after `status=ok` permit merge/release.
## Remediation Checklist
1. Add top-level `LICENSE` file in affected repository.
2. Add SPDX license field in manifest when applicable (`package.json`, `pyproject.toml`, `Cargo.toml`).
3. Re-run scan and verify status transitions to `ok`.
4. Record closure in `DEV_LOGS.md`.

## Outputs
- `infra/governance/LICENSE_AUDIT_REPORT_<date>.json`
- `infra/governance/LICENSE_AUDIT_REPORT_<date>.md`
