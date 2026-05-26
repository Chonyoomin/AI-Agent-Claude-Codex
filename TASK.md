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

Phase 4B - Planner Initial Slice (Proposal Generation)

## Phase Status

Phase 4A (Planning Contract) is closed and approved. Phase 4B implements the first working slice of the automatic planner against the Phase 4A contract: read the current project state, enforce the Phase 4A refusal rules, and generate one valid `.agent-loop/proposed-phase.md` without activating it. The planner may also append decision notes to `.agent-loop/planner.log`. Activation writes (modifying `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json`) are explicitly deferred to a later 4x sub-phase.

## Active Task

Implement the planner's proposal-generation step inside `scripts/agent_loop.py` (or a small adjacent planner module if that keeps ownership boundaries clearer). The planner must: load the planner inputs listed in the Phase 4A contract; apply every refusal and halt condition defined in the contract; generate a `.agent-loop/proposed-phase.md` whose structure matches the contract's required sections in order; enforce the bounded-scope rules on its own generated proposal; optionally append proposal- or refusal-outcome notes to `.agent-loop/planner.log`; and refuse to write any activation file in this sub-phase. Add focused tests for the refusal paths and one valid proposal-generation path. Update `README.md` so the Current Status and usage notes describe the Phase 4B planner slice.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 4 / 4B as active
- `.agent-loop/phase-plan.md` marks Phase 4A complete and contains a Phase 4B section with the same `### Status` / `### Objective` / `### Definition of done` / `### Exclusions` shape as prior sub-phase sections
- `scripts/agent_loop.py` (or a small new planner file) implements: planner input loading, refusal/halt checks, proposal generation, optional `planner.log` notes, and a CLI subcommand to invoke the planner
- `tests/` contains focused tests covering at least the major refusal paths and one valid proposal-generation path
- `README.md` reflects the Phase 4B active status and documents how to invoke the planner
- the planner never writes any file in the Phase 4A "Files the planner must never write" list
- activation writes are NOT implemented in this sub-phase
- no changes to `AGENTS.md`, `CLAUDE.md`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, or the Phase 4A Planning Contract body

## Next-Phase Gate

Do not start the next 4x sub-phase (planner activation writes, planner-orchestrator integration, optional planner adapter, etc.) until:

- this Phase 4B slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- planner activation writes (modifying `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json` based on an approved proposal; deferred to a later 4x sub-phase)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI (would spawn a nested Claude Code session inside the current one - unsafe and outside the operational verification scope)
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any real test/lint/typecheck/build suite to the repository (the new `tests/` directory is for the planner's own validators, not a project-wide CI suite)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
