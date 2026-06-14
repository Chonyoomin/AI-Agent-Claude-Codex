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

Phase 7A - VS Code Task Entrypoints

## Phase Status

Phase 6O (LangChain Support Layer) is closed after Codex review approval and human progression. Phase 7A is now active as the first Phase 7 slice. This sub-phase should add VS Code task entrypoints for common operator flows while preserving the CLI-first contract, keeping repo artifacts as the source of truth, and avoiding any IDE-owned replacement for the shipped orchestrator behavior.

## Active Task

Implement the first VS Code task entrypoints for the agent loop. This slice should add `.vscode/tasks.json` commands for the common operator flows such as running the loop, collecting evidence, opening review artifacts, and other CLI-backed entrypoints, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, or artifact-truth rules.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 7 / 7A as active
- `.agent-loop/phase-plan.md` records Phase 6O as closed history and contains a `## Phase 7A - VS Code Task Entrypoints` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `.vscode/tasks.json` exists and exposes common operator entrypoints as thin wrappers around the shipped CLI surfaces, without introducing IDE-only runtime behavior
- the VS Code tasks preserve canonical repo-artifact truth by invoking the existing orchestrator and evidence-collection commands rather than reimplementing their behavior
- the VS Code tasks preserve the shipped halt/refusal vocabulary, approval-mode behavior, checkpoint/continuation behavior, and artifact ownership boundaries by delegating to existing CLI commands
- the system remains CLI-first: every VS Code task maps to an existing documented command, and the repo remains fully usable without VS Code
- focused tests or validation coverage prove the task definitions point at the intended commands and do not widen scope beyond operator entrypoints
- `README.md` reflects that Phase 7A is active and that VS Code task entrypoints are now the implementation focus

## Next-Phase Gate

Do not start the next 7x sub-phase after Phase 7A until:

- this Phase 7A slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- replacing the CLI-first workflow with a VS Code-only workflow
- artifact dashboards, inspection workflow polish, or reset/recovery UX beyond the narrow task-entrypoint layer for this slice
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
