# LIVE_ACTIVATION_POLICY_REPORT

- generated_at_utc: 2026-02-17T22:47:58.186238+00:00
- status: BLOCKED
- recommended_mode: mock_only
- dirty_repo_budget: 0
- p0_budget: 0

## Checks
| Check | OK | Severity | Details |
|---|---:|---|---|
| network_resolution_gate | 0 | critical | github_dns_resolvable=False |
| submodule_readiness_gate | 0 | critical | live_ready=False, missing_submodule_paths=2 |
| degraded_mode_conformance_gate | 1 | critical | degraded_routes=3, required_assertions=contract+failure |
| dirty_repo_budget_gate | 0 | high | dirty_repos=16, budget=0 |
| p0_gap_budget_gate | 0 | critical | p0_count=9, budget=0 |
| growth_checkpoint_gate | 1 | critical | requires summary.deadloop_cross_repo with cross_repo_assertions+guard+scan+ready all true |
