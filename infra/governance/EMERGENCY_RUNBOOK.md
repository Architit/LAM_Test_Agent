# EMERGENCY RUNBOOK V0.1

## Severity
- P1: life-support/security critical.
- P2: major degradation.
- P3: limited/local issue.

## Global Response Flow
1. Detect event from telemetry/alert.
2. Classify severity and affected domains.
3. Activate containment profile.
4. Execute domain runbook steps.
5. Verify stabilization.
6. Record incident audit and postmortem ticket.

## P1 Immediate Actions (<= 60 sec)
1. Set security lockdown flag.
2. Halt non-critical gateway writes.
3. Preserve audit and telemetry streams.
4. Assign incident commander and fallback owner.
5. Start domain-specific containment.
6. Activate fail-safe guard profile and verify `data_circulation.kill_switch=on`.

## Domain Playbooks
### Life Support
1. Switch to safe mode profile.
2. Enforce minimum service floor.
3. Disable non-essential workloads.
4. Emit rollback request artifact and maintain it until recovery sign-off.

### Water
1. Freeze unsafe routing changes.
2. Prioritize quality-safe sources.
3. Trigger leak/loss anomaly checks.

### Energy
1. Apply load shedding policy.
2. Reserve critical capacity buffer.
3. Shift non-critical jobs to deferred queue.

### Logistics
1. Recompute routes with degraded constraints.
2. Prioritize critical deliveries.
3. Mark blocked routes and ETA impact.

### Security
1. Rotate compromised credentials/tokens.
2. Isolate suspect agents or nodes.
3. Capture forensics snapshot before restore.

## Exit Criteria
- Critical metrics back under threshold for N cycles.
- No active unauthorized actions.
- Incident commander signs recovery decision.

## Post-Incident
- Postmortem within 24h.
- Policy patch and control updates.
- Regression drill added to test cascade.
