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

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10AE - Framework Evaluation Beyond The Native Loop

## Phase Status

Phase 10AE is complete as the latest mainline slice. Fix Phase B1, Fix Phase
B2, and Fix Phase B3 are also complete and approved as remediation work against
the desktop bootstrap flow. The main roadmap currently has no predefined next
mainline Phase 10 sub-phase after 10AE, so the repo is parked back on the main
track awaiting the next human-approved roadmap addition or objective.

## Active Task

The mainline Phase 10 roadmap is complete through Phase 10AE. The current repo
state is awaiting the next mainline roadmap definition or human-directed next
objective after the approved Fix Phase B remediation track.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify the repo as returned to the main
  roadmap after the approved Fix Phase B remediation track
- `.agent-loop/phase-plan.md` records Phase 10AE and Fix Phase B1/B2/B3 as
  closed history
- the repo is ready for a new human-approved mainline phase definition if
  additional work is desired

## Next-Phase Gate

Do not activate further mainline work until:

- a new mainline roadmap slice is defined
- the human approves that next phase activation
- the next slice is written into the canonical phase/task artifacts before
  implementation starts

## Out Of Scope For Current Phase

- fabricating a non-existent `Phase 10AF` without updating the roadmap
- silently reopening a completed Fix Phase B slice
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- implementation work for a new phase before that phase is explicitly defined
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
