# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10G - Minimal External UI Contract

## Status
Phase 10G is active as the next planning/contract slice under Phase 10. The goal is to define the first external operator UI surface for external-workspace mode: its advisory-vs-canonical boundaries, what it may read, what must remain CLI-only, and how it preserves the shipped safety/approval model without yet implementing a UI runtime.

## Task
Define the Minimal External UI Contract for the agent loop. This slice should specify the first external operator UI surface for external-workspace mode: which canonical artifacts it may read, which actions remain CLI-only, how advisory UI state must defer to repo artifacts on disk, and what safety/approval boundaries must remain intact before any UI runtime is implemented.

## Notes

- keep this slice narrow: define only the bounded UI contract; do not broaden into UI runtime, target-side dispatch, or broader workflow control
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future bootstrap or target-dispatch decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- stale or inconsistent external-target state must refuse fail-closed rather than being silently repaired or inferred
- any future UI must be advisory over canonical repo artifacts unless a later approved slice explicitly grants a write path
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
