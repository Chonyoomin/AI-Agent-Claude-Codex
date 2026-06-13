# Claude Code Task

## Phase
Phase 6M - Runtime Adapter Contract For Framework Evaluation

## Objective
Define the Phase 6 runtime adapter contract for framework evaluation. This slice should specify, before any framework-backed runtime is implemented, the adapter boundary alternate runtimes must honor: canonical inputs, allowed writes, halt/refusal behavior, checkpoint and memory interaction rules, approval-mode preservation, artifact-precedence guarantees, and evaluation constraints that keep the shipped local orchestrator as the default source-of-truth runtime.

## Context
Phase 6M is a contract-definition slice, not an implementation slice for LangGraph, LangChain, CrewAI, or any other framework runtime. The repo has already shipped the local Phase 6 memory, checkpoint, continuation, optional-context, and repeated-failure synthesis surfaces through 6L. This phase must define how any future alternate runtime would interoperate with those existing artifact-driven behaviors without superseding canonical repo state, widening autonomy, or bypassing the shipped human-gated workflow. Update the planning/docs artifacts needed for this contract so the next framework-evaluation phase can implement against a clear boundary.

## Required work
- Add a `## Phase 6M - Runtime Adapter Contract For Framework Evaluation` section to `.agent-loop/phase-plan.md` that concretely defines the contract alternate runtimes must satisfy.
- Define the canonical source-of-truth artifacts that alternate runtimes must treat as authoritative over any framework-managed state, including task/phase artifacts, `loop-state.json`, evidence files, review artifacts, durable memory entries, and checkpoints.
- Define allowed reads, allowed writes, and forbidden writes for a future alternate runtime, preserving Codex/Claude/human ownership boundaries and the existing local orchestrator default.
- Define how an alternate runtime must preserve approval-mode behavior, strict-gate semantics, halt/refusal vocabulary, checkpoint/continuation handling, durable-memory interaction, and auditability.
- Define evaluation constraints for future opt-in framework experiments so they can be compared against the shipped local orchestrator without replacing it.
- Update `README.md` so it accurately describes Phase 6M as the active contract-definition slice and explains the scope of this phase at a high level.
- Keep the contract concrete enough that a later implementation phase can build a LangGraph or similar runtime mirror against it without making fresh architectural decisions.

## Files likely involved
- `.agent-loop/phase-plan.md`
- `TASK.md`
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`
- `README.md`
- `ROADMAP.md`

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.
- This is a contract/documentation slice; do not implement any LangGraph, LangChain, CrewAI, or other framework-backed runtime path in code.
- Preserve the shipped local orchestrator as the default runtime and preserve canonical repo-artifact precedence over any future framework state.
- Do not widen autonomy, bypass human gates, or change existing Phase 5 runtime behavior as part of this phase.

## Validation expected
- No new runtime behavior is expected in this slice; focused validation may be limited to artifact consistency checks if no executable behavior changes.
- If any tests or commands are run, record them exactly in `.agent-loop/claude-summary.md`.

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
