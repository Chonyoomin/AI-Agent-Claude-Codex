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

Phase 0 - Instruction Foundation

## Active Task

Establish the instruction foundation and initial loop-control artifacts so future implementation phases can run against a clear, enforced contract.

## Phase Outcome Required Now

- the repository has aligned project instructions
- the repository has a public-safe README
- the repository has a roadmap aligned with the instruction contract
- the repository has initial `.agent-loop/` control files for the first loop iteration
- task and phase ownership are documented clearly

## Next-Phase Gate

Do not start the next phase until:

- the current phase receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next phase

## Out Of Scope For Current Phase

- orchestrator implementation
- evidence collection scripts
- validation automation
- approval mode implementation
- editor integration
- MCP support
