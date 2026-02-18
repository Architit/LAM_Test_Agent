# ARGD Subtree Access Audit (2026-02-18)

## Scope
- Validate `ARGD/Arrierguard` semantic root materialization and operational coverage across ecosystem repos.
- Confirm live policy gates remain open after semantic-topology healing.

## Evidence
- Semantic identity active across layers:
  - `memory/FRONT/SEMANTIC_IDENTITY_MAP_2026-02-17.tsv:11`
  - `memory/AVANGARD/SEMANTIC_IDENTITY_MAP_2026-02-17.tsv:11`
  - `memory/ARCHIVE/SEMANTIC_IDENTITY_MAP_2026-02-17.tsv:11`
  - `memory/GUARD_HEAL/SEMANTIC_IDENTITY_MAP_2026-02-17.tsv:11`
- Physical semantic root now exists:
  - `/home/architit/work/Archivator_Agent/SubtreeHub/ARGD/Arrierguard`
- Artifact groups materialized (9/9):
  - `protocols, contracts, policies, atlas, maps, chronologs, logs, journals, matrices`
- Hash parity sample confirmed:
  - `PROTOCOLS_LIST_2026-02-17.txt` source == ARGD copy (`sha256` match)
- Gateway verification:
  - `/home/architit/work/System-/scripts/gateway_verify_all_repos.sh` => `github=ok` for all listed repos.
- Live policy after healing:
  - `memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT.md` => `status: READY`, `recommended_mode: live_plus_mock`

## Coverage Check
- `ARGD/.../protocols/PROTOCOLS_LIST_2026-02-17.txt` contains 15 ecosystem repo paths.
- `gateway_verify_all_repos.sh` has 15 repos with `github=ok`.
- Delta interpretation:
  - `Archivator_Agent` is intentionally outside operational subtree-target set.
  - `CORE_RECLONE_CLEAN` appears in subtree operational paths but is not in gateway repo list.

## Residual Risk
- Full Archivator refresh completed successfully (`global_refresh:ok` in `/tmp/archivator_refresh.log`).
- `ARGD/Arrierguard` is present in `ecosystem_file_matrix_latest.tsv` (`SubtreeHub/ARGD/Arrierguard/*` rows confirmed).
- Remaining risk is limited to target-scope design of subtree reports (some `github_subtree_*` artifacts cover only predefined repo subset).

## Status
- `ARGD semantic root`: ACTIVE and physically materialized.
- `Subtree operational coverage`: PASS.
- `Live activation gates`: PASS (critical gates green).
- `Residual action`: maintain periodic refresh cadence and keep scope contracts for `github_subtree_*` reports explicit.
