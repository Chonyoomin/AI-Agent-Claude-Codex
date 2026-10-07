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

Fix Phase C5 - Start / Stop Agent Control Surface

## Phase Status

Active and ready for implementation.

## Active Task

Add one primary desktop Start Agent control that becomes a Stop Agent surface while active, with prerequisite and refusal guidance.

## Phase Outcome Required Now

- TASK.md, .agent-loop/current-task.md, .agent-loop/current-phase.md, and .agent-loop/loop-state.json identify Fix Phase C5 as the active sub-phase
- .agent-loop/phase-plan.md records Fix Phase C5 as active
- .agent-loop/claude-prompt.md contains the scoped C5 implementation prompt

## Next-Phase Gate

- the desktop app exposes one clear Start Agent control
- prerequisites disable Start with plain-English guidance
- active execution switches the control to Stop Agent or pause
- start/stop use canonical runtime ownership without bypassing gates

## Out Of Scope For Current Phase

- run-mode selection, Start/Stop controls, and run-console work
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- rewriting contracts in AGENTS.md or CLAUDE.md
- introducing a hidden UI-only state store or second orchestration plane
- fabrication of .agent-loop/codex-review.md content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)







