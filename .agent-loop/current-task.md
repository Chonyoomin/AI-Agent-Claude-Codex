# Current Task

## Phase
Phase 6 - Durable Memory and Optional Context Layer

## Sub-Phase
Phase 6M - Runtime Adapter Contract For Framework Evaluation

## Status
Phase 6M is active as the next slice for durable memory and optional context support. The goal is to define the runtime adapter contract that future framework-backed execution paths must satisfy on top of the shipped 6B/6C/6D/6E/6F/6G/6H/6I/6J/6K/6L memory, checkpoint, continuation, continuation-context, phase-boundary distillation, optional-context loading, prompt-integration, and repeated-failure synthesis runtime while preserving the shipped Phase 5 runtime, reconciliation, and prompt-bootstrap baselines.

## Task
Define the Phase 6 runtime adapter contract for framework evaluation. This slice should specify, before any framework-backed runtime is implemented, the adapter boundary alternate runtimes must honor: canonical inputs, allowed writes, halt/refusal behavior, checkpoint and memory interaction rules, approval-mode preservation, artifact-precedence guarantees, and evaluation constraints that keep the shipped local orchestrator as the default source-of-truth runtime.

## Notes

- keep this slice narrow: define only the runtime adapter contract; do not implement a framework-backed runtime, broader autonomy model, or arbitrary repo-file/context ingestion
- preserve existing Phase 2A / 3A / 4A contracts unchanged
- `.agent-loop/claude-done.json` is a routing signal, not proof of correctness
- preserve the existing Phase 5E post-review reconciliation behavior and the Phase 5F phase-start prompt-bootstrap path unchanged
- memory must remain a supporting layer rather than a competing source of truth over canonical task and loop-state artifacts
- checkpoint artifacts remain additive and must not mutate canonical task / state artifacts except for the existing orchestrator-owned continuation state transitions
- the adapter contract must preserve the shipped Phase 5 strict-gate semantics and require alternate runtimes to refuse stale, contradictory, malformed, unsupported, unreadable, out-of-bound, or unrecognized inputs fail-closed
- do not change the shipped `review`, `strict`, or `autonomous` semantics
