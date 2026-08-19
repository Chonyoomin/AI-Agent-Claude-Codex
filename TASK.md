# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated
local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and
  generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the
Codex and Claude loop carry the project forward phase by phase with review,
fixes, and human gating between phases.

## Active Phase

Fix Phase C - Guided Non-Technical Desktop PRD-To-Run UX

## Active Sub-Phase

Fix Phase C3 - PRD Intake UX

## Phase Status

Implementation complete; approved for human review.

## Active Task

Add the desktop PRD file-picker and selection flow, plain-English missing/invalid/ready states, and a bounded preview of the selected PRD.

## Phase Outcome Required Now

- TASK.md, .agent-loop/current-task.md, .agent-loop/current-phase.md, and .agent-loop/loop-state.json identify Fix Phase C3 as the active sub-phase
- .agent-loop/phase-plan.md records the Fix Phase C track and the concrete Fix Phase C1 through Fix Phase C8 slices
- .agent-loop/claude-prompt.md contains a scoped implementation prompt for the Fix Phase C3 PRD intake slice

## Next-Phase Gate

- the desktop app lets the operator choose a PRD without terminal commands
- the UI distinguishes project ready / PRD missing, invalid PRD, and PRD ready states
- the selected PRD is shown in a bounded preview
- invalid or missing input has plain-English actionable guidance
- the flow does not create a hidden PRD cache or redesign PRD decomposition

## Out Of Scope For Current Phase

- run-mode selection, Start/Stop controls, and run-console work
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- rewriting contracts in AGENTS.md or CLAUDE.md
- introducing a hidden UI-only state store or second orchestration plane
- fabrication of .agent-loop/codex-review.md content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)



