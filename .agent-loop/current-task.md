# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10E - External Workspace Bootstrap Runtime Initial Slice

## Status
Phase 10E is active as the next implementation slice under Phase 10. The goal is to implement the explicit bootstrap runtime for `empty_target` external workspaces: honoring the approved Phase 10C opt-in and refusal rules, writing only the allowed target-side canonical artifact set atomically, and updating controller-owned bootstrap-state metadata without yet adding target-side cycle dispatch or external UI behavior.

## Task
Implement the External Workspace Bootstrap Runtime Initial Slice for the agent loop. This slice should add the explicit bootstrap path for `empty_target` external workspaces under the approved Phase 10C contract, write only the allowed target-side canonical artifact set atomically, update the controller-owned attach record's bootstrap-state fields consistently, and refuse partial or malformed target states without widening into target-side cycle dispatch or external UI behavior.

## Notes

- keep this slice narrow: implement only the bounded bootstrap runtime for empty targets; do not broaden into target-side dispatch, external UI, or broader workflow control
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any future bootstrap or target-dispatch decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external attach/detach behavior aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
