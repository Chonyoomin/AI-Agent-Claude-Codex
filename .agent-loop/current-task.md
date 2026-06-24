# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10F - External Target Validation And Refusal Hardening

## Status
Phase 10F is active as the next implementation slice under Phase 10. The goal is to harden external-workspace safety around attached targets: strengthening validation and refusal behavior for target roots, stale attach state, and malformed external-target artifacts without yet adding target-side cycle dispatch or external UI behavior.

## Task
Implement External Target Validation And Refusal Hardening for the agent loop. This slice should strengthen external-workspace runtime safety by hardening target-root and attach-state validation, expanding malformed-artifact and stale-attach refusal coverage, and tightening controller/target consistency checks without widening into target-side cycle dispatch or external UI behavior.

## Notes

- keep this slice narrow: implement only the bounded validation/refusal hardening for external targets; do not broaden into target-side dispatch, external UI, or broader workflow control
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future bootstrap or target-dispatch decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- stale or inconsistent external-target state must refuse fail-closed rather than being silently repaired or inferred
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
