# Current Task

## Phase
Phase 7 - VS Code Polish

## Sub-Phase
Phase 7C - Status, Reset, And Recovery UX

## Status
Phase 7C is active as the third slice for VS Code polish. The goal is to add clear operator-facing status, reset, and recovery ergonomics in VS Code while preserving the shipped Phase 5 runtime baselines and the shipped Phase 6 memory, checkpoint, runtime-adapter, and support-layer behavior unchanged.

## Task
Implement the VS Code status, reset, and recovery UX layer for the agent loop. This slice should add clear operator-facing run/status/reset ergonomics in VS Code, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, artifact-truth, or recovery semantics.

## Notes

- keep this slice narrow: implement only VS Code status/reset/recovery ergonomics; do not broaden into dashboard UX or VS Code-owned orchestration behavior
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any editor surface
- the VS Code status/reset/recovery layer must preserve the shipped Phase 5 strict-gate semantics and existing refusal behavior by routing through the current workflow rather than replacing it
- do not change the shipped `review`, `strict`, or `autonomous` semantics
