# SEMANTIC_IDENTITY_GOVERNANCE_NORMALIZATION_V1

- date: 2026-02-18
- decision: normalize repo_domain semantic identities from provisional/template placeholders to canonical active identifiers.
- rule: `true_name = <system_id>_CANONICAL`, `status = ACTIVE`.
- scope: only rows with unresolved/provisional/template naming markers.
- exclusions: pre-approved semantic triplets already in ACTIVE state.
