# INITIATION CODE: UPGRADE DEVKIT VALIDATOR (CODE IS TRUTH) ⚜️

**Target:** LAM_Test_Agent (GUARD-01)
**Effective Date:** 2026-03-14
**Classification:** GOVERNANCE ENFORCEMENT (P0-CRITICAL)
**Reference:** IC_PURGE_THE_LIE_20260314.md

## 0. CONTEXT
To prevent future occurrences of "Hallucinated Compliance", the core governance validator must be upgraded. A task cannot pass if it only contains Markdown changes for phases requiring functional algorithms.

## 1. OBJECTIVE
Upgrade the DevKit Validator in the Bridge repository to enforce the "Code is Truth" mandate.

## 2. EXECUTION PARAMETERS
1. **Target Repository:** `/home/architit/work/RADRILONIUMA` (Bridge / CASTLE)
2. **Code Requirements:**
   - Modify `scripts/task_spec_validator.py`.
   - Add a strict requirement to the schema: if a task implies algorithmic execution, it MUST specify `code_evidence_path` (pointing to `.py`, `.sh`, `.cpp`, etc.).
   - The validator must physically verify that the file at `code_evidence_path` exists and contains logic.
   - Throw a new error code `TASKSPEC_MISSING_CODE_EVIDENCE` if this requirement is not met.
3. **Evidence:**
   - Apply the patch to the Bridge repository via standard DevKit rollout (`patch.sh --3way`).
   - Ensure `scripts/test_entrypoint.sh --governance` passes with the new validator logic.

А́мієно́а́э́с моєа́э́ри́э́с ⚜️