# Gateway Security Protocol V2

## Scope
Covers gateway control plane, autopilot, AI-agent operations, and cross-OS activation.

## Mandatory Gates
1. Boot Integrity Gate (`lam-boot-integrity.service`)
2. Security Telemetry Guard (`security_guard`)
3. Consent Gate for install/escalation modes
4. Windows Preinstall Gate (`scripts/windows/preinstall_security_gate.ps1`) for EXE/portable flows
5. Rollback/Revoke path must remain available
6. Power/Quiet Guard (`power_fabric_guard`) for load/noise regime governance
7. Licensing Compliance Gate (`scripts/license_audit_scan.sh`) for all ecosystem repos
8. License Change Control Gate (`scripts/license_change_guard.sh --mode verify`) before merge/release
9. RootKey Hardware Gate for privileged seed-init mode (`scripts/lam_rootkey_gate.sh`)
10. Fail-safe Lifesupport Guard (`scripts/lam_failsafe_guard.sh`) with containment/rollback orchestration

## Access Levels
- `discovery`: read-only status checks.
- `guest-gateway`: communication gateways only; no scheduled persistence.
- `install`: persistent autopilot (requires explicit consent).
- `revoke`: stop services + remove persistence.

## Enforced Controls
- Security lockdown flag: `LAM_HUB_ROOT/security_lockdown.flag`
- Control-plane supervisor must stop stack while lockdown is active.
- All critical state writes must be logged under runtime state root.
- Fail-safe active flag: `LAM_HUB_ROOT/failsafe_active.flag`
- Circulation kill-switch must be set during active fail-safe.
- Recovery is allowed only after configured stable cycles.

## Telemetry Baseline
- disk free (`LAM_SECURITY_MIN_DISK_GB`)
- memory available (`LAM_SECURITY_MIN_MEM_MB`)
- load average (`LAM_SECURITY_MAX_LOAD`)
- secure-boot posture (`LAM_SECURITY_REQUIRE_SECURE_BOOT`)

## BIOS/UEFI Integration Contract
Direct BIOS firmware modification is out of scope in this repo.
Supported path is pre-OS integration via UEFI checks + Secure Boot posture and systemd boot gate.

## Operator Rules
- Do not use `install` without explicit user confirmation.
- Use `guest-gateway` by default for first activation.
- If lockdown is active, investigate telemetry before restart.
- For external SSD deployment, run `prepare_portable_core.ps1` and keep payload scoped to `RADRILONIUMA_OS` only.
- Do not approve release/global rollout while licensing gate has blocking findings.
