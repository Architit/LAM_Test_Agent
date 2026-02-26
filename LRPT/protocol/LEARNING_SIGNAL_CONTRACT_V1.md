# LEARNING SIGNAL CONTRACT V1

contract_type: learning_signal
version: v1
status: ACTIVE
mode: contracts-first, derivation-only
effective_utc: 2026-02-18T01:21:51Z

## Purpose
- Enable In-Situ Self-Evolution without violating the NO runtime logic invariant.
- Distill episodic experience (like the Samsara Deadloop incidents) into static 'Synaptic Weights'.

## Mechanism
- Agents (Codex, Operator) MUST read LRPT/journal/SYNAPTIC_WEIGHTS_V1.yaml as a precondition.
- Weights act as negative/positive prompts (guardrails) during task generation.
- The Architect or Council of Three formally approves new weights via patch.sh.
