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

<<<<<<< Updated upstream
Phase 6N - Experimental LangGraph Runtime Mirror

## Phase Status

Phase 6M (Runtime Adapter Contract For Framework Evaluation) is closed after Codex review approval and human progression. Phase 6N is now active as the next Phase 6 slice. This sub-phase should add an opt-in experimental LangGraph-backed runtime mirror that exercises the Phase 6M adapter contract in code while preserving the shipped local orchestrator as the default runtime, keeping canonical repo artifacts authoritative, and refusing fail-closed on any divergence from the existing halt, checkpoint, memory, and approval-mode behavior.

## Active Task

Implement the first experimental LangGraph runtime mirror for Phase 6. This slice should add an opt-in framework-backed execution path that mirrors the shipped local orchestrator's state-machine behavior, halt/refusal vocabulary, checkpoint and continuation handling, durable-memory boundaries, audit signals, and approval-mode semantics while keeping the current local runtime as the default and preserving canonical repo-artifact precedence over any framework-managed state.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6N as active
- `.agent-loop/phase-plan.md` records Phase 6M as closed history and contains a `## Phase 6N - Experimental LangGraph Runtime Mirror` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes an opt-in experimental LangGraph-backed runtime mirror or equivalent narrow alternate-runtime entry surface that is explicitly subordinate to the shipped local runtime and the Phase 6M adapter contract
- the experimental runtime preserves canonical repo-artifact truth for task / phase / loop-state / evidence / review / memory / checkpoint artifacts and refuses fail-closed on contradiction with framework-managed state
- the experimental runtime mirrors the shipped halt/refusal vocabulary, approval-mode behavior, checkpoint and continuation rules, durable-memory boundaries, and audit expectations closely enough to be evaluated against the local runtime
- the shipped local orchestrator remains the default runtime when no explicit alternate-runtime selection is provided
- focused tests cover runtime selection, default-runtime preservation, representative halt/refusal mirroring, checkpoint/continuation compatibility, and canonical-precedence preservation for the experimental mirror
- `README.md` reflects that Phase 6N is active and that experimental LangGraph runtime mirroring is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6N until:

- this Phase 6N slice receives `APPROVED_FOR_HUMAN_REVIEW`
=======
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
>>>>>>> Stashed changes
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
<<<<<<< Updated upstream
- implementing LangChain support-layer work, CrewAI evaluation, or broader multi-framework orchestration beyond the narrow LangGraph mirror needed for this slice
- changing current planner, activator, evidence-collection, review routing, checkpoint, continuation, memory, or prompt-integration semantics for the default local runtime beyond the narrow opt-in experimental mirror path
=======
- replacing the CLI-first workflow with a VS Code-only workflow
- artifact dashboards, inspection UX, or reset/recovery UX beyond the narrow task-entrypoint layer for this slice
- changing current planner, activator, evidence-collection, review routing, checkpoint, continuation, memory, prompt-integration, runtime-adapter, or LangChain support-layer semantics for the default local runtime
>>>>>>> Stashed changes
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
