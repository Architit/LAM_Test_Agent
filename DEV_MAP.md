# DEV_MAP — INTERACTION_PROTOCOL Refactor Program

## Execution Status (2026-02-12)
- Status: IN PROGRESS (baseline integrated into `INTERACTION_PROTOCOL.md`)
- Integrated blocks: A, B, C, D, E, F, G, H (contract-level baseline)
- Next pass: tighten examples, add repo-specific verification checklists (still policy-only)

## Scope
Full structural refactor of INTERACTION_PROTOCOL.md:
Modules → Modes → Phases → Stages → Steps → Command Contracts.
Primary focus:
- ssn rstrt
- cld rstrt
- Phase alignment gates (fix Phase 2 / Stage C/3 sync issue)

Non-goal:
- Ecosystem evolution roadmap (belongs to ROADMAP.md layer)

---

# WORK PROGRAM (iterative)

## A) Structural Normalization
A1. Introduce module architecture (M0–M5)
A2. Unify terminology (Phase/Stage/Step)
A3. Remove ambiguity in STOP rules

Deliverable: contradiction-free document skeleton.

---

## B) Output Modes Specification
B1. Define Mode N (Normal)
B2. Define Mode R (Recovery — strict 2-line format)
B3. Define deterministic mode switching

Deliverable: explicit I/O contract layer.

---

## C) ssn rstrt Full Specification
C1. Deterministic phase mapping (ACTIVE vs NEW)
C2. Finite-state machine definition
C3. Explicit STOP gates
C4. Handoff gate definition

Deliverable: contradiction-free Session Restart protocol.

---

## D) cld rstrt Full Specification
D1. Environment sync layer
D2. SS-layer verification
D3. Minimal recovery constraints
D4. Deterministic phase alignment

Deliverable: Cold Restart protocol with no semantic gaps.

---

## E) Phase Alignment Gate (Fix C/3)
E1. Define Phase Context object
E2. Define allowed phase-set after restart
E3. Define snapshot alignment rule
E4. Define conflict resolution rule

Deliverable: synchronized restart → execution transition.

---

## Governance
Changes to INTERACTION_PROTOCOL.md follow:
DEV_LOGS → ROADMAP → INTERACTION_PROTOCOL → commit + push


---

## F) Index Sync Hardening (Process Correction)

Problem:
`git diff --stat` does not show untracked files, causing false "no changes" perception.

Solution:
F1. Mandatory `git status -sb` before any Safety Check.
F2. If `??` present → must stage explicitly before diff.
F3. Safety Check sequence becomes:
    - git status -sb
    - git add <file> (if needed)
    - git diff --cached --stat
    - key file diff
F4. No commit allowed without visible staged diff.

Deliverable: Execution Cycle updated to remove index visibility gap.


---

## G) EXPORT Completion Verification (Contract-bound)

Problem:
Checking file existence does NOT guarantee that session context export is complete.

Requirement:
EXPORT is considered complete only if state files:
- conform to their respective CONTRACT documents,
- contain derived facts of the current session,
- reflect current phase/export markers where applicable.

Rules:
G1. File presence alone is NOT a valid verification criterion.
G2. EXPORT must validate contract ↔ state semantic consistency.
G3. If mismatch detected → Phase 1 remains incomplete.
G4. Verification must be read-only and derivation-only.

Deliverable:
Explicit contract-bound definition of EXPORT completion in restart protocols.

---

## H) Protocol Phase Scale (1 / 0 / -1)

Purpose:
Add deterministic tri-phase intent marker to development protocol mapping.

Definition:
- `+1` — execution-forward phase (allowed only when all gates are green)
- `0` — governance/synchronization phase (planning/review/sync; execution transition forbidden)
- `-1` — recovery/conflict phase (alignment mismatch or restart ambiguity; execution blocked)

Rules:
- H1. Enter `0` during Governance Review Stage and protocol synchronization.
- H2. Enter `-1` on snapshot/roadmap/protocol mismatch or unresolved restart conflict.
- H3. Transition to `+1` only after phase-alignment and handoff gates are satisfied.
- H4. Policy-only marker; no automation, no runtime enforcement.

Semantic interpretation:
- `+1` = positive
- `0` = neutral
- `-1` = negative

7-language semantic labels:
- Russian (ru): `+1` положительный, `0` нейтральный, `-1` отрицательный
- English (en): `+1` positive, `0` neutral, `-1` negative
- Chinese (zh): `+1` 正向, `0` 中性, `-1` 负向
- Arabic (ar): `+1` إيجابي, `0` محايد, `-1` سلبي
- Afrikaans (af): `+1` positief, `0` neutraal, `-1` negatief
- Japanese (ja): `+1` ポジティブ, `0` ニュートラル, `-1` ネガティブ
- Spanish (es): `+1` positivo, `0` neutro, `-1` negativo

Deliverable:
Compact and deterministic phase-intent encoding for protocol map and snapshot handoff.
