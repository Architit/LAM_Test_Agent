# Phase 3.2.A — Ecosystem Structural Definition (Contract)

This document defines the **Ecosystem Structural Layer** as a **non-runtime**, **repo-native** contract.

Hard constraints:
- contracts-first
- observability-first
- derivation-only
- **NO runtime logic**
- **NO execution-path impact**

This layer is **structural documentation only**.

---

## 1. Scope

Phase 3.2 defines:
- what an ecosystem **integration container** is (repo-native artifact),
- how it is **distributed** (git subtree strategy — future),
- how entities are **named** (3-level naming model),
- and strict boundaries vs Task Spec Layer (Phase 3.1.C).

---

## 2. Non-goals (hard)

This layer **MUST NOT** introduce:
- task registry / task storage authority,
- task runner / orchestrator,
- runtime services, daemons, hooks,
- build-time or CI enforcement logic,
- new execution paths.

---

## 3. Separation of responsibilities

- **LAM / Taskarid**: Source of Truth for real Task Specs and task-domain logic.
- **DevKit (this repo)**: execution tooling and declarative contracts only.
- **Ecosystem Structural Layer**: structural containers + naming + distribution strategy (no runtime).

---

## 4. Structural entities (first tree)

### 4.1 Root container
- True-name: **Loarachspoiszat**
- Public nickname: **Larpat**
- System ID: **LRPT**

Role: first ecosystem structural container (repo-native, non-runtime).

### 4.2 Task-domain home
- True-name: **Tendshpoisat**
- Call sign: **Taspit**
- System ID: **TSPT**

Role: task-home domain subsection under the first tree (non-agent, non-runtime).

---

## 5. 3-level naming model (contract)

Every structural entity has exactly three name levels:
1) **True-name** — architect key (canonical)
2) **Public nickname** — human-facing call sign
3) **System ID** — machine identifier / address

This is a **system rule**, not an incidental convention.

---

## 6. Distribution strategy (contract-level intent)

Future distribution for ecosystem containers is **git subtree**:
- repo-native import
- avoids submodule friction
- allows local adaptations
- remains non-runtime

No subtree implementation is introduced in this phase.

---

## 7. Observability requirements

When structural decisions are changed:
- record the decision in `ROADMAP.md`
- log completion in `DEV_LOGS.md`
- keep changes atomic and derivation-only
