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

Phase 2A - Evidence Collection Contract

## Active Task

Define the command-discovery and logging contract for evidence collection so the Phase 2B script (`scripts/run_checks.sh`) can be built later against a precise, predictable specification. Planning and documentation only; the script itself is intentionally not implemented in this sub-phase.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 2 / 2A as active
- `.agent-loop/phase-plan.md` records the Phase 2A objective, definition of done, exclusions, and the full Evidence Collection Contract
- `README.md` documents that Phase 2A is the current operating mode and points readers at the contract
- `ROADMAP.md` reflects the 2A / 2B decomposition of Phase 2
- the contract is concrete enough that Phase 2B can be implemented from it without further design decisions

## Next-Phase Gate

Do not start Phase 2B (or any later phase) until:

- Phase 2A receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase or phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase or phase

## Out Of Scope For Current Phase

- implementation of `scripts/run_checks.sh` (Phase 2B)
- orchestrator implementation (Phase 3)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- adding any real test/lint/typecheck/build suite to the repository (this is still a documentation-only project)
- creating fabricated `.agent-loop/git-diff.patch`, `.agent-loop/git-status.log`, or `.agent-loop/*-output.log` files
