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

Phase 3 - Scripted Orchestrator MVP

## Active Sub-Phase

Phase 3B - Implement `scripts/agent_loop.py` (initial slice)

## Phase Status

Phase 3A is complete and approved by the human to advance. The Orchestrator Contract is frozen at `.agent-loop/phase-plan.md` under `## Phase 3A - Orchestrator Contract`. Phase 3B implements `scripts/agent_loop.py` against that contract. This initial slice covers the scaffold and the normal-cycle control path only; fix-cycle automation, real Claude/Codex subprocess adapters, approval modes, Git automation, and editor integration are deferred to later 3x sub-phases.

## Active Task

Implement the first working slice of `scripts/agent_loop.py`: repository-root discovery, `.agent-loop/loop-state.json` load/validate/save helpers that honor the orchestrator's allowed write set, artifact validation scaffolding (prompt presence, Claude summary structure + `## Phase` match, Codex review structure + single-verdict parse, evidence-file presence + contract-vocabulary `state:` field), the normal-cycle control path (Claude adapter boundary -> `scripts/run_checks.sh` -> wait for `codex-review.md` -> parse verdict -> branch), and fail-closed halt behavior for malformed or missing required artifacts. The Claude and Codex adapter boundaries exist as real Python classes; their current implementations are manual-handoff stubs that pause for the human to drive the actual CLIs.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3B as active
- `.agent-loop/phase-plan.md` marks Phase 3A complete and contains a Phase 3B section
- `scripts/agent_loop.py` exists, is runnable on a Python 3 + Bash system, and implements the normal-cycle control path against the Phase 3A contract
- the orchestrator never writes any file outside the contract's allowed set; the per-cycle artifact validators halt the loop with the contract's `halted_*` status vocabulary
- `README.md` reflects the Phase 3B active status and documents how to invoke the orchestrator
- no fix-cycle automation, no real subprocess-driven Claude/Codex adapters, no approval modes, no Git automation, and no editor integration are introduced in this slice

## Next-Phase Gate

Do not start the next 3x sub-phase (fix-cycle automation, real Claude/Codex subprocess adapters, etc.) until:

- this Phase 3B slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- fix-cycle automation (deferred to a later 3x sub-phase)
- real subprocess-driven Claude or Codex CLI adapters (the only adapters wired up in this slice are manual-handoff stubs)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- any change to the Phase 2A Evidence Collection Contract
- any change to `scripts/run_checks.sh`
- any change to the Phase 3A Orchestrator Contract
- adding any real test/lint/typecheck/build suite to the repository (still a documentation-only project)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
