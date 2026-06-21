# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10C - External Workspace Bootstrap Contract

## Status
Phase 10C is active as the next planning slice under Phase 10. The goal is to define the bootstrap contract for target-side `.agent-loop` initialization in external-workspace mode: what may be bootstrapped, what must be refused, what operator opt-ins are required, and how partial bootstrap stays fail-closed before any runtime implementation ships.

## Task
Define the External Workspace Bootstrap Contract for the agent loop. This slice should specify how target-side `.agent-loop` initialization may occur in external-workspace mode, which canonical artifacts may be created or refused, what operator decisions and bootstrap states must be recorded, and how later Phase 10D/10E runtime slices depend on that bootstrap contract.

## Notes

- keep this slice narrow: define the bootstrap contract only; do not broaden into attach runtime, bootstrap runtime implementation, or UI implementation
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future attach/detach or bootstrap decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
