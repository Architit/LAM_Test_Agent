# LAM_Test_Agent

Integration test harness for LAM agent interaction flows.

## Bootstrap
```bash
scripts/bootstrap_submodules.sh
```

`devkit/bootstrap.sh` now includes gateway auto-recovery for Gemini/MCP.
Controls:
- `LARPAT_GATEWAY_AUTOHEAL=1` (default): run auto-heal.
- `LARPAT_GATEWAY_STRICT=1`: fail bootstrap if auto-heal fails.

## Cloud Fabric (Drive + Multi-Cloud)
Central CLI for storage sync/migration:
```bash
scripts/cloud_fabric.sh verify
scripts/cloud_fabric.sh disk-status
scripts/cloud_fabric.sh route-table
scripts/cloud_fabric.sh monitor-space
scripts/cloud_fabric.sh sync-gdrive
scripts/cloud_fabric.sh snapshot
scripts/cloud_fabric.sh fanout governance
scripts/cloud_fabric.sh full-cycle governance
```

Environment:
- `CF_SCOPE=gateway` (default): sync only gateway folder, not full repo.
- `CF_GATEWAY_LOCAL_DIR`: local import/export gateway directory.
- `CF_GDRIVE_ROOT`: local Google Drive mirror root (device+cloud mode).
- `CF_ROUTE_FILE`: class routing CSV (`class,remote_path,min_free_gb`).

## LAM Local Gateway (MCP-optional)
Unified local gateway for all agents with provider routing and health checks:
```bash
scripts/lam_gateway.sh init
scripts/lam_gateway.sh health
scripts/lam_gateway.sh route governance
scripts/lam_gateway.sh put ./DEV_LOGS.md --class governance
scripts/lam_gateway.sh list --class governance
scripts/lam_gateway.sh enqueue-put ./DEV_LOGS.md --class governance
scripts/lam_gateway.sh run-queue --max-jobs 20
scripts/lam_gateway.sh monitor --once --auto-switch
scripts/lam_gateway.sh policy-check --class sensitive --provider gdrive --contract-id CTR-001 --approval-ref APR-001
scripts/lam_gateway.sh circulation-kill-switch status
scripts/gateway_circulation_killswitch.sh on
python3 scripts/gateway_apply_circulation_policy.py
scripts/lam_realtime_circulation.sh --once
```

Provider roots are local filesystem adapters:
- `local`: `.gateway/storage/local`
- `gdrive`: `$GATEWAY_GWORKSPACE_ROOT/LAM_GATEWAY/<repo>`
- `onedrive`: `$GATEWAY_ONEDRIVE_ROOT/LAM_GATEWAY/<repo>`
- `archive`: `$GATEWAY_ARCHIVE_ROOT/LAM_GATEWAY/<repo>`

Gateway state files:
- policy: `.gateway/routing_policy.json`
- index: `.gateway/index.json`
- queue: `.gateway/queue.json`
- circuit breakers: `.gateway/circuit_breakers.json`

`routing_policy.json` supports:
- hard local free-space floor (`routing.local_hard_min_free_gb`)
- queue retry/backoff (`queue.max_attempts`, `queue.backoff_base_sec`, `queue.backoff_cap_sec`)
- circuit breaker (`circuit_breaker.failure_threshold`, `circuit_breaker.cooldown_sec`)
- provider size caps (`provider_limits.<provider>.max_object_mb`)
- governed circulation controls (`data_circulation.*`) with kill-switch and class/provider/org policy gates

Governed transfer flags:
- `put ... --contract-id <id> --approval-ref <ref>`
- `enqueue-put ... --contract-id <id> --approval-ref <ref>`
- `policy-check ...` to pre-validate transfer against gates
- `circulation-kill-switch on|off|status` for emergency gate control

## Desktop Console UI (Local-First)
Terminal-native desktop UI with direct local adapters (no CLI transit layer):
```bash
scripts/lam_console.sh
scripts/interactionface.sh
```

`interactionface.sh` launches the same core UI with branded profile and tuned defaults for portable/WSL environments.
Theme words are configurable via `LAM_UI_THEME_WORDS` (default includes `shadow blur light liquid glass ... core face`).
Touch profile:
- `LAM_UI_PROFILE=touch` (default in `interactionface.sh`)
- larger tab hit-zones
- slower hover dwell
- soft scroll inertia
- liquid pulse on hovered tabs
- realtime activity wallpaper (driven by `activity_telemetry_state.json`)
- mirror-inertia orchestration across pane zones:
  - `LAM_UI_MIRROR_FLOW_STRENGTH`
  - `LAM_UI_ZONE_FLOW_DECAY`
  - `LAM_UI_ZONE_FLOW_INJECT`
- inversion mirror feedback (audio + haptic queue):
  - `LAM_UI_AUDIO_FEEDBACK`
  - `LAM_UI_HAPTIC_FEEDBACK`
  - `LAM_UI_FEEDBACK_FLOW_THRESHOLD`
  - `LAM_UI_FEEDBACK_MIN_INTERVAL_SEC`
  - haptic event queue: `.gateway/bridge/captain/haptic_feedback_queue.jsonl`
- external ambient mirror vectors (Aura-style):
  - `LAM_UI_AMBIENT_LIGHT_ENABLED`
  - `LAM_UI_AMBIENT_LIGHT_INTERVAL_SEC`
  - `LAM_UI_AMBIENT_LIGHT_MAX_BRIGHTNESS`
  - vector state: `.gateway/bridge/captain/ambient_light_vector.json`
  - vector stream: `.gateway/bridge/captain/ambient_light_vectors.jsonl`

Main commands inside UI:
- `help`
- `agents`
- `health`
- `route <class> [size_bytes]`
- `send <agent> <message>`
- `model <codex|gemini> <message>`
- `enqueue-put <path> [class]`
- `run-queue [max_jobs]`
- `bridge-status`
- `open-gate <windows|linux|macos> [endpoint]`
- `list-gates`
- `register-device <id> <type> <platform> [endpoint]`
- `list-devices`
- `send-device <id> <message>`
- `mcp-status`
- `gws-health`
- `gws-sync <push|pull>`
- `gws-list [prefix] [limit]`

## RADRILONIUMA Site + OS Subdomain
Run install portal:
```bash
scripts/run_install_portal.sh 8099
```
Open in browser:
- `http://127.0.0.1:8099`
- Main brand site label: `RADRILONIUMA`
- OS install gateway label: `os.radriloniuma`
- OS label text is configurable in `apps/install_portal/app.js` (`OS_BRAND_LABEL`)

One-click install entrypoints used by portal:
- Linux/macOS shell: `scripts/install_oneclick.sh`
- Windows PowerShell: `scripts/windows/install_oneclick.ps1`

Public domain/subdomain proxy config:
```bash
DOMAIN=radriloniuma.example.com \
OS_SUBDOMAIN=os.radriloniuma.example.com \
scripts/deploy_public_site.sh
```
Run Caddy directly from generated config:
```bash
DOMAIN=radriloniuma.example.com \
OS_SUBDOMAIN=os.radriloniuma.example.com \
scripts/deploy_public_site.sh --run-caddy
```

UI controls:
- Keyboard: `1..9,0` panes, `Tab` next pane, `PgUp/PgDn` scroll
- Mouse: click pane tabs on top row, wheel scroll inside active pane
Interactionface dynamics:
- hover-dwell expands tab surfaces
- idle-delay zoom shifts UI depth (surface expansion)
- realtime scrollbar thumb at right edge
- keyboard navigation: `Left/Right` pane switch, `Up/Down` fine scroll

Optional model adapters:
- `LAM_CODEX_ENDPOINT=http://127.0.0.1:...`
- `LAM_GEMINI_ENDPOINT=http://127.0.0.1:...`

If endpoints are absent, model requests are spooled to `.gateway/hub/model_spool/*.jsonl`.

Background model delivery worker (retry/backoff/circuit-breaker/dead-letter):
```bash
scripts/lam_model_worker.sh --once
scripts/lam_model_worker.sh --interval-sec 5
```

Portal gateway daemon (cross-OS interface translation):
```bash
scripts/lam_portal_gateway.sh --mode auto --host 127.0.0.1 --port 8765
```
Modes:
- `http`: REST gateway on `127.0.0.1:8765`
- `file`: bridge bus in `.gateway/bridge/captain/portal_{status,commands,results}.json*`
- `auto`: try HTTP, fallback to file mode

Bridge stack orchestration (worker + portal):
```bash
scripts/lam_bridge_stack.sh start
scripts/lam_bridge_stack.sh status
scripts/lam_bridge_stack.sh stop
```
By default stack uses `LAM_PORTAL_MODE=file` for maximum compatibility.
On `start`, stack auto-syncs data circulation policy template into gateway policy
(`LAM_APPLY_CIRCULATION_POLICY_ON_START=1` by default).
Stack also starts:
- `mcp_watchdog`: automatic `google-workspace` MCP health-check + heal (`gemini auth clear`, reinstall extension)
- `gws_bridge`: local queue-based Google Workspace bridge (MCP-independent path)
- `security_guard`: runtime telemetry + security policy checks (disk/mem/load/secure-boot posture)
- `role_orchestrator`: realtime role rebinding after device wake/resume
- `power_fabric_guard`: CPU/GPU/RAM/swap/I-O + quiet-hours noise-aware orchestration
- `realtime_circulation`: global sync loop + inversion circulation of test reports
- `device_mesh_daemon`: verified device sync queue for paired devices
- `activity_telemetry`: runtime activity + archive/db telemetry stream
- `ambient_light`: mirrored ambient-light dispatch to external devices (`ambient_light` scope)
- `io_spectral`: vector spectral analysis of I/O/input-response frequencies and latency
- `governance_autopilot`: realtime governance expansion cycle across protocol/plan/analysis/strategy/contracts/policy/instructions/revision/licensing/map/topology/chronology
- `media_sync`: realtime stream sync between device storage and removable media with microtick isolation locks
  - default priority order: `instructions -> contracts -> protocols -> policies -> licenses -> map -> cards -> keypass_code_dnagen -> other`
- `rootkey_gate`: physical removable-root authorization gate for Architit initiation key (`SEED_GOD_MODE_SPREAD_FLOW_INIT`)
- `external_provider_mesh`: external sync/readiness mesh (GitHub, Google, Microsoft, OpenAI, Claude, xAI, Shinkai, Ollama, NVIDIA/Intel/AMD)
- `feedback_gateway`: autopilot feedback/recommendation routing to external gateway channels with spool fallback
  - safety gate: during lockdown/failsafe non-critical feedback is blocked; critical uses `LAM_FEEDBACK_CRITICAL_ALLOWED`

Role orchestration controls:
```bash
scripts/lam_rolectl.sh status
scripts/lam_rolectl.sh profiles
scripts/lam_rolectl.sh set-profile portable_core
scripts/lam_rolectl.sh rebind-now
```
Profile override is persisted at `LAM_HUB_ROOT/role_profile.override`.
Selector policy: `infra/security/role_selector.json`.
Hardware/security-aware role switches:
- `LAM_ROLE_DEGRADE_ON_BATTERY=1`
- `LAM_ROLE_MAX_LOAD_BEFORE_DEGRADE=16`
- `LAM_ROLE_MAX_TEMP_BEFORE_DEGRADE_C=82`
- `LAM_WAKE_STRICT_SECURE_GATE=0|1` (block wake actions if secure posture is invalid)
- `LAM_ROLE_REASON_HOLD_THRESHOLD=3` (activate hold runbook on repeated critical reason-codes)

Standalone controls:
```bash
scripts/lam_mcp_watchdog.sh --once
scripts/lam_mcp_watchdog.sh --once --heal-now
scripts/lam_gws_bridge.sh --once
scripts/lam_power_fabric_guard.sh --once
scripts/power_profilectl.sh status
scripts/power_profilectl.sh set turbo
scripts/power_profilectl.sh set quiet
scripts/power_profilectl.sh set auto
scripts/lam_activity_telemetry.sh --once
scripts/lam_ambient_light.sh --once
scripts/lam_io_spectral.sh --once
scripts/lam_governance_autopilot.sh --once
scripts/lam_media_sync.sh --once
scripts/lam_rootkey_gate.sh --once
scripts/lam_external_provider_mesh.sh --once
scripts/lam_feedback_gateway.sh --once
scripts/provider_mesh_bootstrap.sh verify
scripts/provider_mesh_bootstrap.sh apply
scripts/rootkey_pair.sh pair --owner architit --key-id AK-001
scripts/rootkey_challenge.sh issue --ttl-sec 180
scripts/rootkey_challenge.sh solve
scripts/rootkey_pair.sh status
scripts/lam_realtime_circulation.sh --status
scripts/lam_realtime_circulation.sh --daemon --interval-sec 12
scripts/license_audit_scan.sh
scripts/license_change_guard.sh --mode verify
```

Provider bootstrap template:
- copy `scripts/provider-secrets.env.example` -> `scripts/provider-secrets.env`
- fill secrets/roots, then run `scripts/provider_mesh_bootstrap.sh apply`
- `scripts/lam_bridge_stack.sh` auto-sources `scripts/provider-secrets.env` if present

System-level (root) propagation:
```bash
sudo scripts/power_profilectl.sh set quiet --system
sudo scripts/power_profilectl.sh clear --system
```

Windows parallel gateway launch (Windows Terminal + browser portal):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/lam_portals.ps1
```

WSL autopilot after reboot (Windows logon trigger):
```bash
scripts/register_wsl_autopilot.sh
```
Or directly from PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/register_wsl_autopilot.ps1
```

Portable EXE installer bundle (Windows):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/build_exe_installer.ps1
```
Output bundle:
- `scripts/windows/dist/RADRILONIUMA_Installer.exe`
- `scripts/windows/dist/portable_activate.ps1`
- `scripts/windows/dist/register_wsl_autopilot.ps1`
- `scripts/windows/dist/preinstall_security_gate.ps1`
- `scripts/windows/dist/prepare_portable_core.ps1`

Run `RADRILONIUMA_Installer.exe` from external SSD to:
- request user consent
- start bridge stack in WSL
- register autopilot task on Windows logon
- open branded installer wizard (default run mode)

Installer modes (`portable_activate.ps1`):
- `-Mode discovery`: only inspect status
- `-Mode guest-gateway`: open communication gateways only (default)
- `-Mode install`: gateway + autopilot registration
- `-Mode revoke`: stop stack + remove autopilot task

Silent mode:
- `RADRILONIUMA_Installer.exe /S`
  - maps to `-Silent -AssumeConsent -Mode install`
  - requires policy override: `RADR_ALLOW_SILENT_INSTALL=1`

Wizard:
- default EXE launch opens `installer_wizard.ps1`
- includes mode selector, preflight audit button, portable SSD prep button, rollback button, logs viewer

Security preflight (standalone):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/preinstall_security_gate.ps1 -Mode guest-gateway
```
Checks:
- WSL availability/reachability
- required script set present
- minimum free disk space (mode-sensitive)
- optional Secure Boot requirement (`RADR_REQUIRE_SECURE_BOOT=1`)
- install mode elevation requirement

Portable SSD core preparation (D/E/F external storage):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/prepare_portable_core.ps1 -TargetDrive D:
```
Creates `D:\RADRILONIUMA_OS` with minimal runtime tree + launcher:
- `Start_RADRILONIUMA_OS.cmd`
- `portable_manifest.txt`

Note:
- Modern Windows blocks true USB autorun for executables on plug-in.
- Reliable model is consented launcher + scheduled task/host policy.

## Mobile / Wearables / Earbuds Integration
Onboard device tokens:
```bash
scripts/mobile_onboard.sh device_phone_1 phone android
scripts/mobile_onboard.sh device_phone_2 phone ios
scripts/mobile_onboard.sh device_watch_1 watch wearos
scripts/mobile_onboard.sh device_audio_1 earbuds earbuds
scripts/device_meshctl.sh pair pixel8 phone android wifi telemetry_read,device_status,test_reports --endpoint http://127.0.0.1:8765
scripts/device_meshctl.sh pair-profile samsung_android s24 --endpoint http://127.0.0.1:8765
scripts/device_meshctl.sh pair-profile ambient_rgb aura_hub --endpoint usb://ambient
scripts/device_meshctl.sh promote-full-access s24
scripts/device_meshctl.sh sync-once all bidirectional
```

Bridge device commands (inside `lam_console`):
- `register-device device_phone_1 phone android http://127.0.0.1:8765`
- `list-devices`
- `send-device device_phone_1 "sync now"`

Device gateway details:
- `infra/mobile/DEVICE_GATEWAYS.md`
- `infra/mobile/MULTIDEVICE_MESH_PROTOCOL_V1.md`

Realtime mesh daemon:
```bash
scripts/lam_device_mesh_daemon.sh --interval-sec 15 --direction bidirectional
```

## Autonomous Boot (Native Linux, not WSL)
One-command host bootstrap (services + autopilot):
```bash
sudo scripts/autonomous_bootstrap.sh full --install-deps
```

Autopilot now deploys a full control-plane supervisor service (stack mode):
- starts `model_worker`, `portal_gateway`, `mcp_watchdog`, `gws_bridge`
- writes persistent runtime state under `/var/lib/lam-runtime/<repo>/...`
- uses `/etc/default/lam-control-plane` as runtime env file
- applies boot integrity gate (`lam-boot-integrity.service`) before control plane start

Security protocol references:
  - `infra/security/GATEWAY_SECURITY_PROTOCOL_V2.md`
  - `infra/security/FAILSAFE_LIFESUPPORT_PROFILE_V1.md`
  - `infra/security/POWER_SYNC_AND_QUIET_PROTOCOL_V1.md`
  - `infra/security/AGENT_OPERATOR_INSTRUCTIONS.md`
  - `infra/security/LICENSE_COMPLIANCE_PROTOCOL_V1.md`
  - `infra/security/ROLE_ORCHESTRATION_PROTOCOL_V1.md`
  - `infra/security/ROOTKEY_HARDWARE_GATE_PROTOCOL_V1.md`
  - `infra/governance/IO_SPECTRAL_ANALYSIS_PROTOCOL_V1.md`
  - `infra/governance/AUTOPILOT_GOVERNANCE_EXPANSION_PROTOCOL_V1.md`
  - `infra/governance/MEDIA_STREAM_SYNC_PROTOCOL_V1.md`

RootKey 2FA hardening:
- automatic challenge rotation (`LAM_ROOTKEY_CHALLENGE_AUTO_ROTATE_SEC`)
- fail2ban threshold on repeated `challenge_response_mismatch`:
  - `LAM_ROOTKEY_FAIL_THRESHOLD`
  - `LAM_ROOTKEY_BAN_SEC`

Realtime circulation crypto mirror:
- signed inversion bundle sidecars (`.sig.json`)
- HMAC verify on ingest in required mode:
  - `LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR`
  - primary: `LAM_CIRCULATION_HMAC_KEY` or `LAM_CIRCULATION_HMAC_KEY_FILE`
  - secondary (grace window): `LAM_CIRCULATION_HMAC_SECONDARY_KEY` or `LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE`
  - rotation state: `LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE`
  - grace control: `LAM_CIRCULATION_HMAC_SECONDARY_GRACE_SEC` or `LAM_CIRCULATION_HMAC_SECONDARY_VALID_UNTIL_EPOCH`
  - `LAM_CIRCULATION_HMAC_KEY_ID`
- scheduled key rotation daemon:
  - `scripts/lam_hmac_rotation_daemon.sh --daemon --interval-sec 86400`
  - `scripts/lam_hmac_rotate.sh rotate|status|clear-secondary`
- Governance control pack:
  - `infra/governance/MASTER_PLAN_LIVE_CORRECTION_V0_1.md`
  - `infra/governance/AGENT_CONTRACT_TEMPLATE.md`
  - `infra/governance/STRUCTURAL_SYSTEMS_MAP_V1.md`
  - `infra/governance/STRUCTURAL_SYSTEMS_CONTRACTS_V1.md`
  - `infra/governance/EXTERNAL_FEEDBACK_GATEWAY_PROTOCOL_V1.md`
  - `infra/governance/DIRECTIVE_VECTOR_MAP.md`
  - `infra/governance/EMERGENCY_RUNBOOK.md`
  - `infra/governance/CROSS_ORG_DATA_CIRCULATION_PROTOCOL.md`
  - `infra/governance/GATEWAY_CIRCULATION_POLICY_TEMPLATE.json`
  - `infra/governance/GLOBAL_REALTIME_CIRCULATION_PROTOCOL_V1.md`
  - `infra/governance/FAILSAFE_GOVERNANCE_CONTRACT_V1.md`
- System services:
  - `lam-boot-integrity.service`
  - `lam-security-telemetry.service`
  - `lam-power-fabric.service`
  - `lam-hmac-rotation.service` (early-boot crypto key rotation)
  - `lam-control-plane.service`

Fail-safe lifecycle guard:
- daemon: `scripts/lam_failsafe_guard.sh --interval-sec 8`
- one-shot: `scripts/lam_failsafe_guard.sh --once`
- force activation: create `LAM_HUB_ROOT/failsafe_force.flag`
- state: `LAM_HUB_ROOT/failsafe_guard_state.json`

Bare-metal image path (BIOS/UEFI boot flow):
```bash
sudo scripts/build_autonomous_os_image.sh --output /tmp/lam-autonomous.img --size-gb 16
```

Details:
- `infra/autonomous_os/README.md`

## Hardened Boot Pipeline (UEFI + SecureBoot + Recovery/OTA)
Hardened image build:
```bash
sudo scripts/build_autonomous_os_image_hardened.sh \
  --output /tmp/lam-autonomous-hardened.img \
  --size-gb 24
```

Optional Secure Boot signing:
```bash
sudo scripts/build_autonomous_os_image_hardened.sh \
  --output /tmp/lam-autonomous-hardened.img \
  --secure-boot-sign \
  --sb-key /path/to/db.key \
  --sb-cert /path/to/db.crt
```

OTA bundle:
```bash
scripts/prepare_ota_bundle.sh --image /tmp/lam-autonomous-hardened.img --channel stable
```

Recovery switch:
```bash
sudo scripts/recovery_switch.sh request
sudo scripts/recovery_switch.sh reboot
```

Details:
- `infra/autonomous_os/HARDENED_IMAGE_PIPELINE.md`

## Run tests
```bash
./.venv/bin/python -m pytest -q
```

### Split Modes
```bash
scripts/test_entrypoint.sh --unit-only
scripts/test_entrypoint.sh --integration
scripts/test_entrypoint.sh --ci
scripts/test_entrypoint.sh --cascade-quick
scripts/test_entrypoint.sh --cascade-standard
scripts/test_entrypoint.sh --cascade-full
scripts/test_entrypoint.sh --microtick-quick
scripts/test_entrypoint.sh --microtick-standard
scripts/test_entrypoint.sh --microtick-full
scripts/test_entrypoint.sh --bg-start
scripts/test_entrypoint.sh --bg-status
scripts/test_entrypoint.sh --bg-errors
scripts/test_entrypoint.sh --bg-stop
scripts/test_entrypoint.sh --isolation-status
```

Notes:
- Integration tests that require submodule agent sources are marked `submodule_required`.
- If submodules are absent, those tests are skipped with explicit reason.
- Cascade modes execute stages/phases sequentially and stop on first failure.
- Cascade artifacts: `.gateway/test_runs/<run_id>/summary.json` and per-phase logs.
- Microtick modes run tiny test batches (mostly 1 file per tick) with timeout and resume state.
- Microtick isolation orchestration:
  - tests execute in isolated workspace copy: `.gateway/test_zones/<run_id>/workspace`
  - active test scopes are file-locked (`chmod a-w`) during tick execution
  - completed zones are logged for post-test debugging
- Microtick artifacts:
  - `.gateway/test_runs/<run_id>/microtick_progress.tsv`
  - `.gateway/test_runs/<run_id>/microtick_summary.json`
  - `.gateway/test_zones/<run_id>/locks.tsv`
  - `.gateway/test_zones/<run_id>/zones.tsv`
- Controls:
  - `LAM_TEST_TICK_TIMEOUT_SEC` (default `120`)
  - `LAM_TEST_MAX_TICKS` (default `0`, unlimited)
  - `LAM_TEST_RESUME=1` (default, skip already recorded ticks)
  - `LAM_TEST_ISOLATE_WORKSPACE=1` (default)
  - `LAM_TEST_FS_LOCK_ENABLED=1` (default)

Windows cascade launcher:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/test_phase_cascade.ps1 -Mode standard
```
Windows microtick launcher:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/test_microtick_cascade.ps1 -Mode standard -MaxTicks 10
```

Quiet background testing (non-blocking):
- starts daemon that executes microticks in the background
- records realtime failures to `.gateway/test_runs/background/errors.jsonl`
- keeps your terminal free for live debugging work

Linux/WSL:
```bash
scripts/test_background_daemon.sh start --mode standard
scripts/test_background_daemon.sh status
scripts/test_background_daemon.sh errors --lines 40
scripts/test_background_daemon.sh watch
scripts/test_background_daemon.sh stop
```

Windows wrapper:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/test_background_daemon.ps1 -Action start -Mode standard
```

## Current Test Scale
- Collected tests: `160`
- Typical local result (unit-only local profile): `134 passed, 26 deselected`

## CI Gates
- `quality`: `ruff` + `mypy` + ecosystem deadloop guard (`--ecosystem`) + safety/resource stack validation + growth snapshot + bounded growth backlog generation + live activation policy report
- `quality`: `ruff` + `mypy` + ecosystem deadloop guard (`--ecosystem`) + safety/resource stack validation + growth snapshot + bounded growth backlog generation + live activation policy report + phase E drift report
- `unit-runtime-cov`: unit tests with runtime-only coverage gate (`>=65%`)
- `integration`: integration/route suites (submodule-dependent tests are skipped when sources are absent)

## Growth Data
- Route-level growth telemetry snapshot:
  - `memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json`
- Bounded growth backlog artifact:
  - `memory/FRONT/TEST_MATRIX_GROWTH_BACKLOG.md`

## Ecosystem Governance
- Protocol expansion strategy:
  - `memory/FRONT/ECOSYSTEM_PROTOCOL_EXPANSION_STRATEGY_2026-02-17.md`
- Safety/resource stack (machine-readable):
  - `memory/FRONT/ECOSYSTEM_SAFETY_RESOURCE_STACK_V1.json`
- Ecosystem telemetry baseline:
  - `memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT_2026-02-17.json`
  - `memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT_2026-02-17.md`
- Live activation policy report:
  - `memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT_2026-02-17.json`
  - `memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT_2026-02-17.md`
- Phase E drift report:
  - `memory/FRONT/PHASE_E_DRIFT_REPORT_2026-02-17.json`
  - `memory/FRONT/PHASE_E_DRIFT_REPORT_2026-02-17.md`

## Strategy Artifacts
- WB-01 deep analysis and evolution plan:
  - `WB01_LAM_TEST_AGENT_DEEP_ANALYSIS_AND_STRATEGY_2026-02-17.md`
- Mirror gap strategy for discovering missing future-architecture tests:
  - `TEST_GAP_MIRROR_STRATEGY_2026-02-17.md`
- Route mirror matrix and compatibility report:
  - `TEST_MIRROR_MATRIX.md`
  - `COMPATIBILITY_MATRIX_REPORT_2026-02-17.md`
