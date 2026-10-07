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

Fix Phase C7 - Review And Approval Surface

## Phase Status

Active and ready for implementation.

## Active Task

Add a plain-English desktop review and approval surface for approval-required pauses with explicit gated actions.

## Phase Outcome Required Now

- TASK.md, .agent-loop/current-task.md, .agent-loop/current-phase.md, and .agent-loop/loop-state.json identify Fix Phase C7 as the active sub-phase
- .agent-loop/phase-plan.md records Fix Phase C7 as active
- .agent-loop/claude-prompt.md contains the scoped C7 implementation prompt

## Next-Phase Gate

- the desktop app explains what is waiting, why approval is required, the recommended action, and what happens next
- the operator can take an explicit review or approval action through the existing canonical gate owner
- missing identity, refusal, strict-mode, and recovery rules remain enforced
- advanced technical details remain available without making raw artifacts the default view
- the surface does not auto-approve, write UI-only state, or create a second orchestration plane
## Out Of Scope For Current Phase

- run-mode selection, Start/Stop controls, and run-console work
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- rewriting contracts in AGENTS.md or CLAUDE.md
- introducing a hidden UI-only state store or second orchestration plane
- fabrication of .agent-loop/codex-review.md content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)












