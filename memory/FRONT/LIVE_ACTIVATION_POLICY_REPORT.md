# LIVE_ACTIVATION_POLICY_REPORT

- generated_at_utc: 2026-02-18T00:43:01.204989+00:00
- status: READY
- recommended_mode: live_plus_mock
- dirty_repo_budget: 0
- p0_budget: 0

## Checks
| Check | OK | Severity | Details |
|---|---:|---|---|
| network_resolution_gate | 1 | critical | github_dns_resolvable=False, local_dependency_mirror_ready=True |
| submodule_readiness_gate | 1 | critical | live_ready=True, missing_submodule_paths=0 |
| degraded_mode_conformance_gate | 1 | critical | degraded_routes=3, required_assertions=contract+failure |
| dirty_repo_budget_gate | 0 | high | dirty_repos=16, budget=0 |
| p0_gap_budget_gate | 1 | critical | p0_count=0, budget=0 |
| growth_checkpoint_gate | 1 | critical | requires summary.deadloop_cross_repo with cross_repo_assertions+guard+scan+ready all true |
| archivator_handoff_gate | 1 | critical | requires Archivator mirror freshness for workflow snapshots when scope_active=true; scope_active=True, handoff_ok=True, missing=0, stale=0 |
| semantic_identity_governance_gate | 1 | critical | blocks rollout on unresolved/provisional/template identity naming in subtree maps; scope_active=True, identity_ok=True, unresolved=0, provisional=0, templated=0 |
