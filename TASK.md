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

Phase 2 - Evidence Collection Automation

## Active Sub-Phase

Phase 2B - Implement scripts/run_checks.sh

## Active Task

Implement `scripts/run_checks.sh` against the approved Phase 2A Evidence Collection Contract. Implementation only; do not redesign the contract.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 2 / 2B as active
- `.agent-loop/phase-plan.md` records Phase 2A as complete and Phase 2B as active without changing the contract text
- `scripts/run_checks.sh` exists, is executable, and implements the Phase 2A contract exactly
- `README.md` documents how to run the script and reflects the Phase 2B status
- the script has been run at least once and the evidence files in `.agent-loop/` reflect a real run

## Next-Phase Gate

Do not start Phase 3 (or any later phase) until:

- Phase 2B receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next phase

## Out Of Scope For Current Phase

- orchestrator implementation (`scripts/agent_loop.py`, Phase 3)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- any change to the Phase 2A Evidence Collection Contract
- adding any real test/lint/typecheck/build suite to the repository (still a documentation-only project)
- creating `.agent-loop/checks.json` (script must work with or without it)
