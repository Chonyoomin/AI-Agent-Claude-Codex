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

Phase 4A - Planning Contract

## Phase Status

Phase 3 (Scripted Orchestrator MVP) is closed; the orchestrator, evidence capture, verdict handling, and live-run verification work it covered is treated as the established prior chapter for the purposes of activating Phase 4. Phase 4A is planning and documentation only: define the contract that a future automatic phase planner must satisfy. No planner code is written in this sub-phase; the planner implementation itself is deferred to a later 4x sub-phase activated only after 4A is approved.

## Active Task

Define the Phase 4A planning contract for automatic next-phase generation in `.agent-loop/phase-plan.md`. The contract must specify: which inputs the planner reads (read-only), which artifacts the planner is allowed to write, ownership boundaries with respect to existing Codex- and Claude-owned files, what fields a valid generated phase or sub-phase proposal must contain (label, objective, definition of done, exclusions, files likely involved, contract-change disclosure, cycle-size estimate, dependencies), bounded-scope rules (size limits, testability, forbidden-file list), human-approval requirements (proposals may be written autonomously; activation requires explicit human approval), refusal / halt conditions for unsafe or underspecified proposals, and how the planner must handle unresolved review verdicts, halted loop state, or stale evidence. No planner code; documentation only.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 4 / 4A as active
- `.agent-loop/phase-plan.md` records Phase 3 as closed and contains a Phase 4 umbrella section plus a Phase 4A section that defines the Planning Contract
- the Phase 4A contract is concrete enough that a later 4x sub-phase could implement the planner against it without further design decisions
- `README.md` reflects the Phase 4A active status and frames the next system capability accurately
- `ROADMAP.md` reflects the 4A / later-4x decomposition of Phase 4 without changing overall project scope
- no planner code is created in this sub-phase
- no changes to `scripts/agent_loop.py`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, `AGENTS.md`, or `CLAUDE.md`

## Next-Phase Gate

Do not start the next 4x sub-phase (planner implementation, planner adapter, etc.) until:

- this Phase 4A slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- implementation of any planner code (deferred to a later 4x sub-phase)
- automatic activation of proposed phases (activation always requires explicit human approval; the planner only proposes)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to `scripts/agent_loop.py` or `scripts/run_checks.sh`
- adding any real test/lint/typecheck/build suite to the repository (still a documentation-only project)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
