# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10D - External Workspace Attach/Detach Runtime Initial Slice

## Status
Phase 10D is active as the next implementation slice under Phase 10. The goal is to implement the minimal attach/detach runtime path for external-workspace mode: selecting a target, enforcing the approved ownership/path boundaries, writing and removing the controller-owned attach record, and recording bounded attach/detach audit behavior without yet adding full bootstrap automation.

## Task
Implement the External Workspace Attach/Detach Runtime Initial Slice for the agent loop. This slice should add the minimal runtime path that selects an external target, validates the approved ownership/path boundaries, writes and removes the controller-owned attach record under the approved contract, and records bounded attach/detach audit behavior without yet performing full target bootstrap automation.

## Notes

- keep this slice narrow: implement the minimal attach/detach runtime only; do not broaden into full bootstrap runtime, target-side dispatch, or UI implementation
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future attach/detach or bootstrap decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
