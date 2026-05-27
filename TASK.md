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

Phase 4C - Planner Activation Writes

## Phase Status

Phase 4B (Planner Initial Slice) is closed and approved for human review. Phase 4C implements the activation step the Phase 4A Planning Contract authorizes: consume an already-generated `.agent-loop/proposed-phase.md` whose `## Approval` section carries the literal `APPROVED_FOR_ACTIVATION` token AND references the proposal's `## Label`, then perform only the activation writes the Phase 4A contract permits (`TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md` append-only, `.agent-loop/loop-state.json` reset per the contract). Planner-orchestrator auto-integration and the optional planner adapter remain deferred.

## Active Task

Implement a separate `activate` CLI path in `scripts/agent_loop.py` (NOT folded into `plan`) that: parses `.agent-loop/proposed-phase.md`; verifies a human-authored `## Approval` section exists, contains the literal `APPROVED_FOR_ACTIVATION` token on its own line within that section, and references the proposal's `## Label` text; refuses on a missing approval section, a malformed/mis-cased/decorated token, a label mismatch, an unreadable proposal, an unreadable loop-state.json, or any malformed required proposal section; on success performs ONLY the Phase 4A activation writes (rewriting `TASK.md`'s `## Active Phase` / `## Active Sub-Phase` / `## Phase Status` / `## Active Task` / `## Phase Outcome Required Now` / `## Next-Phase Gate` / `## Out Of Scope For Current Phase` while preserving `## Human Objective` and `## Project Intent` verbatim; rewriting `.agent-loop/current-task.md` and `.agent-loop/current-phase.md`; appending one new sub-phase section to `.agent-loop/phase-plan.md` and updating its `## Active Phase` line; resetting `.agent-loop/loop-state.json` to `status = awaiting_claude_implementation`, `cycle_count = 0`, `last_verdict = null`, `last_verdict_phase = null` with `phase` / `sub_phase` / `task` set from the approved proposal and `max_cycles` / `contract_version` / `claude_version` / `codex_version` / `orchestrator_version` preserved); records the approval source (file path, mtime, literal approval line) into `.agent-loop/planner.log` as a `note:`-style line; and exits 0 on success, 2 on any refusal. Add focused tests for the activation success path and every refusal condition. Update `README.md`.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 4 / 4C as active
- `.agent-loop/phase-plan.md` marks Phase 4B complete and contains a Phase 4C section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` exposes a new `activate` CLI subcommand whose exit code is 0 on a successful activation and 2 on any refusal; activation is NOT folded into the existing `plan` subcommand
- the activation parser refuses every Phase 4A-required refusal path: missing `## Approval` section, missing-or-malformed `APPROVED_FOR_ACTIVATION` token (wrong case, extra words on the line, leading/trailing characters), label-mismatch against `## Label`, missing/unreadable `proposed-phase.md`, missing/malformed `loop-state.json`, and empty required-proposal-section bodies
- on success, the activation path writes ONLY the files the Phase 4A contract authorizes on activation: `TASK.md` (preserving `## Human Objective` and `## Project Intent` verbatim), `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md` (`## Active Phase` line + APPEND new sub-phase section), `.agent-loop/loop-state.json` (reset per contract), and a `note:`-style line in `.agent-loop/planner.log` recording the approval source
- the existing planner-only write boundary (proposal generation step) remains unchanged outside the activation path
- `tests/test_planner_activation.py` exists and covers the activation success path plus every refusal condition above
- `README.md` documents the new `activate` subcommand and operator flow
- no planner-orchestrator auto-integration in this sub-phase
- no changes to `AGENTS.md`, `CLAUDE.md`, `scripts/run_checks.sh`, the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, or the Phase 4A Planning Contract body

## Next-Phase Gate

Do not start the next 4x sub-phase (planner-orchestrator integration, optional planner adapter, etc.) until:

- this Phase 4C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- planner-orchestrator auto-integration (deferred to Phase 4D)
- optional planner adapter (deferred to Phase 4E or later)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any project-wide CI suite to the repository (the new test file is for the activator's own validators)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
