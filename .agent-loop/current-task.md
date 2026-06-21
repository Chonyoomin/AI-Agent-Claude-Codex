# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10A - External Workspace Controller Contract

## Status
Phase 10A is active as the first planning slice under Phase 10. The goal is to define, before implementation, how this agent system can safely control or attach to an external target workspace or repository while preserving explicit controller-vs-target ownership boundaries, canonical artifact truth, refusal behavior, and the shipped CLI-first safety model.

## Task
Define the External Workspace Controller Contract for the agent loop. This slice should specify how the controller repo can target a different workspace or repository safely, what remains controller-owned versus target-owned, where `.agent-loop` artifacts live, how attach/bootstrap and refusal behavior must work, and which later Phase 10 slices implement those behaviors.

## Notes

- keep this slice narrow: define the external-workspace controller contract only; do not broaden into bootstrap/runtime/UI implementation
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any documentation surface
- any capacity-halt retry, re-probe, or automatic-resume decision must originate from canonical repo artifacts rather than transient UI/chat state or a parallel control plane
- any external-workspace control decision must originate from explicit contract rules rather than transient UI/chat state or implicit path assumptions
- do not change the shipped `review`, `strict`, or bounded `autonomous` semantics
- keep future external control aligned with the shipped halt/refusal vocabulary, checkpoint/resume behavior, ownership boundaries, and human approval requirements
