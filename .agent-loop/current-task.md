# Current Task

## Phase
Phase 7 - VS Code Polish

## Sub-Phase
Phase 7B - Artifact Inspection And Review Workflow

## Status
Phase 7B is active as the second slice for VS Code polish. The goal is to make the shipped review and evidence artifacts easy to open and inspect from VS Code while preserving the shipped Phase 5 runtime baselines and the shipped Phase 6 memory, checkpoint, runtime-adapter, and support-layer behavior unchanged.

## Task
Implement the VS Code artifact-inspection and review workflow layer for the agent loop. This slice should make Codex review artifacts, fix prompts, active task/phase artifacts, and evidence logs easy to open and inspect from VS Code, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, or artifact-truth rules.

## Notes

- keep this slice narrow: implement only VS Code artifact-inspection workflow ergonomics; do not broaden into dashboard UX, reset/recovery UX, or VS Code-owned orchestration behavior
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any editor surface
- the VS Code inspection layer must preserve the shipped Phase 5 strict-gate semantics and existing refusal behavior by routing through the current workflow rather than replacing it
- do not change the shipped `review`, `strict`, or `autonomous` semantics
