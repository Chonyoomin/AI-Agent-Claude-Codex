# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the Codex and Claude loop carry the project forward phase by phase with review, fixes, and human gating between phases.

## Active Phase

Phase 6 - Durable Memory and Optional Context Layer

## Active Sub-Phase

Phase 6M - Runtime Adapter Contract For Framework Evaluation

## Phase Status

Phase 6L (Repeated-Failure Memory Synthesis Initial Slice) is closed after Codex review approval and human progression. Phase 6M is now active as the next Phase 6 slice. This sub-phase should define the runtime adapter contract that any future framework-backed execution path must satisfy so LangGraph, LangChain-adjacent helpers, or other alternate runtimes can be evaluated without weakening canonical repo-artifact truth, human approval gates, ownership boundaries, or the shipped local orchestrator defaults.

## Active Task

Define the Phase 6 runtime adapter contract for framework evaluation. This slice should specify, before any framework-backed runtime is implemented, the adapter boundary alternate runtimes must honor: canonical inputs, allowed writes, halt/refusal behavior, checkpoint and memory interaction rules, approval-mode preservation, artifact-precedence guarantees, and evaluation constraints that keep the shipped local orchestrator as the default source-of-truth runtime.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6M as active
- `.agent-loop/phase-plan.md` records Phase 6L as closed history and contains a `## Phase 6M - Runtime Adapter Contract For Framework Evaluation` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the Phase 6M contract defines the adapter boundary that future framework-backed runtimes must satisfy before any LangGraph, LangChain-adjacent, or similar runtime path is implemented
- the contract preserves canonical repo-artifact truth for `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json`, evidence files, review artifacts, memory entries, and checkpoints
- the contract defines allowed inputs, allowed writes, halt/refusal behavior, checkpoint and durable-memory interaction, approval-mode preservation, and audit expectations for alternate runtimes
- the contract explicitly keeps the shipped local orchestrator as the default runtime and treats framework-backed execution as optional future evaluation rather than replacement behavior
- the contract forbids widening autonomy, bypassing human gates, mutating Codex-owned planning artifacts, or treating framework state as superior to canonical repo artifacts
- `README.md` reflects that Phase 6M is active and that runtime-adapter contract definition is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6M until:

- this Phase 6M slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing any LangGraph, LangChain, CrewAI, or other framework-backed runtime path in code during this contract slice
- changing current planner, activator, adapter, evidence-collection, review routing, checkpoint, continuation, memory, or prompt-integration runtime behavior beyond documenting the future adapter boundary
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any project-wide CI suite to the repository beyond focused approval-mode coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
