# Current Task

## Phase
Phase 7 - VS Code Polish

## Sub-Phase
Phase 7A - VS Code Task Entrypoints

## Status
Phase 7A is active as the first slice for VS Code polish. The goal is to add thin VS Code task entrypoints for common operator flows on top of the shipped CLI surfaces while preserving the shipped Phase 5 runtime baselines and the shipped Phase 6 memory, checkpoint, runtime-adapter, and support-layer behavior unchanged.

## Task
Implement the first VS Code task entrypoints for the agent loop. This slice should add `.vscode/tasks.json` commands for the common operator flows such as running the loop, collecting evidence, opening review artifacts, and other CLI-backed entrypoints, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, or artifact-truth rules.

## Notes

- keep this slice narrow: implement only VS Code task entrypoints for existing operator flows; do not broaden into dashboard UX, reset/recovery UX, or VS Code-owned orchestration behavior
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- repo artifacts must remain the source of truth over any editor surface
- VS Code tasks must delegate to existing shipped commands rather than reimplementing their behavior
- the VS Code task layer must preserve the shipped Phase 5 strict-gate semantics and existing refusal behavior by routing through the current CLI entrypoints
- do not change the shipped `review`, `strict`, or `autonomous` semantics
