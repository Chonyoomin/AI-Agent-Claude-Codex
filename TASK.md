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

## Phase Status

Complete - awaiting human approval to advance to Phase 2

## Active Task

Prove the Codex/Claude/human workflow end to end using only files and documented handoffs, with no orchestrator script and no validation automation.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3A as active
- `.agent-loop/phase-plan.md` records Phase 2 / 2B as complete history and contains a Phase 3A section that defines the Orchestrator Contract
- the contract concretely specifies orchestrator inputs, allowed writes, prohibited writes, normal-cycle order of operations, fix-cycle order of operations, evidence-capture invocation, version-aware adapter layer, fail-closed artifact schema validation, verdict handling, `loop-state.json` updates (including `claude_version`, `codex_version`, `orchestrator_version`, and `contract_version` metadata), cycle counting, stop conditions, and prohibited actions
- `.agent-loop/loop-state.json` carries `contract_version`, `claude_version`, `codex_version`, and `orchestrator_version` fields per the contract
- `README.md` reflects the Phase 3A active status and points readers at the contract
- `ROADMAP.md` reflects the 3A / 3B decomposition of Phase 3
- no `scripts/agent_loop.py` is created

## Next-Phase Gate

Do not start Phase 3B (or any later phase) until:

- Phase 3A receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to Phase 3B
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for Phase 3B

## Out Of Scope For Current Phase

- orchestrator implementation (Phase 3)
- evidence collection script `scripts/run_checks.sh` (Phase 2)
- validation automation
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
