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

Phase 4 - Phase Planning Automation

## Active Sub-Phase

Phase 4D - Planner-Orchestrator Integration

## Phase Status

Phase 4C (Planner Activation Writes) is closed and approved for human review. Phase 4D integrates the Phase 4B/4C planner flow into the orchestrator's post-approval path: after a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict is persisted, the orchestrator refreshes `.agent-loop/proposed-phase.md` by invoking the standalone planner, logs the outcome once, and leaves activation as a separate human-approved step. The optional planner adapter remains deferred.

## Active Task

Integrate the standalone planner into the orchestrator's post-approval handoff without auto-activating proposals. After `run_normal_cycle` or the fix-cycle path persists a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict, the orchestrator should invoke the existing planner once, surface planner refusals without converting the overall cycle into a halt, refresh `.agent-loop/proposed-phase.md` only through the planner's existing write boundary, and log the planner invocation result exactly once. Add focused tests for the successful integration path, a planner-refusal path, and a proof that the integration never performs activation writes. Update `README.md`.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 4 / 4D as active
- `.agent-loop/phase-plan.md` marks Phase 4C complete and contains a Phase 4D section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` invokes the existing standalone planner after a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict is persisted, from both the normal-cycle and fix-cycle paths where applicable
- the integration writes at most one planner-invocation note to `.agent-loop/orchestrator.log` per eligible terminal approval and does not convert a planner refusal into an orchestrator halt
- the planner's existing write boundary remains unchanged under integration: only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` may be written by the planner call, and activation remains separate from planning
- no activation write is performed by the integration path; `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, and `.agent-loop/loop-state.json` are not rewritten by the orchestrator's planner hook
- `tests/` contains focused coverage for one successful integration call, one planner-refusal path surfaced without halting the orchestrator, and one proof that the integration never performs activation writes
- `README.md` reflects the Phase 4D active status and documents the post-approval planner refresh behavior
- no changes to `AGENTS.md`, `CLAUDE.md`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, or the Phase 4A Planning Contract body

## Next-Phase Gate

Do not start the next 4x sub-phase (optional planner adapter, etc.) until:

- this Phase 4D slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- optional planner adapter (deferred to Phase 4E or later)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- planner-driven activation from inside the orchestrator (planning may refresh `.agent-loop/proposed-phase.md`, but approval + activation remain a separate human step)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any project-wide CI suite to the repository (the new test file is for the activator's own validators)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
