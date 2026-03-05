# PATCH_RUNTIME_CONTRACT_V1

version: v1.1.0
last_updated_utc: 2026-03-05T00:00:00Z
status: ACTIVE

## Runtime Requirements
1. Runtime MUST use `git apply --index --3way`.
2. Runtime MUST run precheck via `git apply --check --3way` before apply.
3. Runtime MUST require `--sha256 <64hex>`.
4. Runtime MUST require `--task-id <id>`.
5. Runtime MUST require `--spec-file <path>` and compute non-empty `spec_hash`.
6. Runtime MUST emit machine-readable fields (`status`, `error_code`).
7. Runtime MUST emit trace tuple:
   `trace: task_id=<...> spec_hash=<...> artifact_hash=<...> apply_result=<...> commit_ref=<...>`
8. Conflict precheck failure MUST return `status=conflict_detected`, `error_code=PATCH_CONFLICT_DETECTED`.
9. Integrity mismatch MUST return `status=integrity_mismatch`, `error_code=PATCH_SHA256_MISMATCH`.
