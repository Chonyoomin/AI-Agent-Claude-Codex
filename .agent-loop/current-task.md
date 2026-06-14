# Current Task

## Phase
Phase 7 - VS Code Polish

## Sub-Phase
<<<<<<< Updated upstream
Phase 6N - Experimental LangGraph Runtime Mirror

## Status
Phase 6N is active as the next slice for durable memory and optional context support. The goal is to implement the first opt-in experimental LangGraph-backed runtime mirror on top of the shipped 6B/6C/6D/6E/6F/6G/6H/6I/6J/6K/6L memory, checkpoint, continuation, continuation-context, phase-boundary distillation, optional-context loading, prompt-integration, repeated-failure synthesis, and 6M runtime-adapter contract surfaces while preserving the shipped Phase 5 runtime, reconciliation, and prompt-bootstrap baselines.

## Task
Implement the first experimental LangGraph runtime mirror for Phase 6. This slice should add an opt-in framework-backed execution path that mirrors the shipped local orchestrator's state-machine behavior, halt/refusal vocabulary, checkpoint and continuation handling, durable-memory boundaries, audit signals, and approval-mode semantics while keeping the current local runtime as the default and preserving canonical repo-artifact precedence over any framework-managed state.

## Notes

- keep this slice narrow: implement only the opt-in LangGraph runtime mirror needed to exercise the 6M adapter contract; do not broaden into LangChain support-layer work, CrewAI evaluation, or broader autonomy
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- memory must remain a supporting layer rather than a competing source of truth over canonical task and loop-state artifacts
- checkpoint artifacts remain additive and must not mutate canonical task / state artifacts except for the existing orchestrator-owned continuation state transitions
- the experimental mirror must preserve the shipped Phase 5 strict-gate semantics and refuse stale, contradictory, malformed, unsupported, unreadable, out-of-bound, or unrecognized inputs fail-closed
=======
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
>>>>>>> Stashed changes
- do not change the shipped `review`, `strict`, or `autonomous` semantics
