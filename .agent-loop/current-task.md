# Current Task

## Phase
Phase 6 - Durable Memory and Optional Context Layer

## Sub-Phase
Phase 6O - LangChain Support Layer

## Status
Phase 6O is active as the next slice for durable memory and optional context support. The goal is to implement a narrow LangChain support layer on top of the shipped 6B/6C/6D/6E/6F/6G/6H/6I/6J/6K/6L memory, checkpoint, continuation, continuation-context, phase-boundary distillation, optional-context loading, prompt-integration, repeated-failure synthesis, and 6N runtime-adapter surfaces while preserving the shipped Phase 5 runtime, reconciliation, and prompt-bootstrap baselines.

## Task
Implement the LangChain support layer for Phase 6. This slice should add optional LangChain-based helpers only for prompt construction, selective retrieval, and tool abstraction layers while keeping the existing local orchestrator and the shipped Phase 6N LangGraph runtime mirror as the only runtime-control surfaces, preserving canonical repo-artifact precedence and avoiding any promotion of LangChain into a top-level orchestrator role.

## Notes

- keep this slice narrow: implement only the optional LangChain support layer needed for prompt, retrieval, and tool abstraction work; do not broaden into CrewAI evaluation, broader multi-framework orchestration, or a LangChain-owned top-level runtime
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- memory must remain a supporting layer rather than a competing source of truth over canonical task and loop-state artifacts
- checkpoint artifacts remain additive and must not mutate canonical task / state artifacts except for the existing orchestrator-owned continuation state transitions
- the LangChain support layer must preserve the shipped Phase 5 strict-gate semantics and refuse stale, contradictory, malformed, unsupported, unreadable, out-of-bound, or unrecognized inputs fail-closed
- do not change the shipped `review`, `strict`, or `autonomous` semantics
