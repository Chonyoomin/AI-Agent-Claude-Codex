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

Phase 4F - Alternate Planner Adapter Selection

## Phase Status

Phase 4E (Optional Planner Adapter) is closed and approved for human review. Phase 4F is now active and implements adapter selection behind the Phase 4E seam so planner execution can use either the default in-process adapter or one alternate adapter path, while keeping the current local behavior as the fallback and preserving the planner write boundary. Activation remains a separate human-approved step.

## Active Task

Implement adapter selection behind the planner-adapter seam so both the `plan` command path and the post-approval planner refresh path can dispatch through either the default local adapter or one alternate adapter path, while preserving the current local behavior as the fallback. Keep the planner's write boundary unchanged, add focused tests for selection and fallback behavior, and update `README.md`.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, and `.agent-loop/loop-state.json` identify Phase 4 / 4F as active
- `.agent-loop/phase-plan.md` marks Phase 4E complete and contains a Phase 4F section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` selects the planner adapter through a narrow, explicit configuration path instead of always instantiating the local adapter
- the default local planner adapter remains the fallback when no alternate adapter is configured or when configuration is invalid for the alternate path
- exactly one alternate planner adapter path is implemented, and it preserves the Phase 4A planner write boundary and the separate activation step
- planner refusals and planner exceptions remain surfaced with the same fail-closed behavior already required by Phases 4B through 4E
- `tests/` contains focused coverage for adapter selection, local fallback behavior, the alternate adapter path, and proof that the selection logic does not widen planner or activation writes
- `README.md` reflects the Phase 4F active status and documents how planner-adapter selection works
- no changes to `AGENTS.md`, `CLAUDE.md`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, or the Phase 4A Planning Contract body

## Next-Phase Gate

Do not start the next 4x sub-phase after Phase 4F until:

- this Phase 4F slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- planner-driven activation from inside the orchestrator (planning may refresh `.agent-loop/proposed-phase.md`, but approval + activation remain a separate human step)
- multiple alternate planner adapters or plugin/registry discovery for planner adapters
- approval mode implementation (Phase 5)
- durable memory, token-reset continuation, checkpoint-resume logic, and continuation chaining (Phase 6)
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any project-wide CI suite to the repository beyond focused planner-adapter coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
