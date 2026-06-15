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

Phase 7 - VS Code Polish

## Active Sub-Phase

Phase 7C - Status, Reset, And Recovery UX

## Phase Status

Phase 7B (Artifact Inspection And Review Workflow) is closed after Codex review approval and human progression. Phase 7C is now active as the third Phase 7 slice. This sub-phase should add clear operator-facing status, reset, and recovery ergonomics in VS Code while preserving the CLI-first contract, keeping repo artifacts as the source of truth, and avoiding any IDE-owned replacement for the shipped orchestrator behavior.

## Active Task

Implement the VS Code status, reset, and recovery UX layer for the agent loop. This slice should add clear operator-facing run/status/reset ergonomics in VS Code, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, artifact-truth, or recovery semantics.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 7 / 7C as active
- `.agent-loop/phase-plan.md` records Phase 7B as closed history and contains a `## Phase 7C - Status, Reset, And Recovery UX` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the VS Code integration exposes clear status, reset, and recovery ergonomics for the shipped agent-loop workflow without becoming a parallel source of truth
- any new VS Code entrypoints preserve canonical repo-artifact truth by delegating to existing repo artifacts and shipped commands rather than synthesizing alternate state or bypassing recovery rules
- the VS Code status/reset/recovery layer preserves the shipped halt/refusal vocabulary, approval-mode behavior, checkpoint/continuation behavior, and artifact ownership boundaries by remaining a thin operator convenience layer over the existing workflow
- the system remains CLI-first: the repo remains fully usable without VS Code, and the status/reset/recovery workflow must not become a VS Code-only control plane
- focused tests or validation coverage prove the status/reset/recovery workflow points at the intended artifacts or commands and does not widen runtime or ownership scope
- `README.md` reflects that Phase 7C is active and that VS Code status/reset/recovery ergonomics are now the implementation focus

## Next-Phase Gate

Do not start the next 7x sub-phase after Phase 7C until:

- this Phase 7C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- replacing the CLI-first workflow with a VS Code-only workflow
- artifact dashboards beyond the narrow status/reset/recovery layer for this slice
- changing current planner, activator, evidence-collection, review routing, checkpoint, continuation, memory, prompt-integration, runtime-adapter, or LangChain support-layer semantics for the default local runtime
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
