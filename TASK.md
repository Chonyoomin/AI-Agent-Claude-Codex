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

Phase 1 - Manual File-Based Loop

## Active Task

Prove the Codex/Claude/human workflow end to end using only files and documented handoffs, with no orchestrator script and no validation automation.

## Phase Outcome Required Now

- the repository's task and phase control files reflect Phase 1 as the active phase
- the phase plan records the Phase 1 definition of done aligned with `ROADMAP.md`
- the repository documents how the manual loop is run, so a human can execute one full cycle by hand using the existing artifact formats from `AGENTS.md`
- the repository is ready to capture, for the first real review cycle, a manual Claude prompt, Claude summary, git diff, git status, validation logs, Codex review, and fix prompt (if needed) - all as files under `.agent-loop/`
- `README.md` reflects that the manual file-based loop is the current operating mode

## Next-Phase Gate

Do not start the next phase until:

- the current phase receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next phase

## Out Of Scope For Current Phase

- orchestrator implementation (Phase 3)
- evidence collection script `scripts/run_checks.sh` (Phase 2)
- validation automation
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
