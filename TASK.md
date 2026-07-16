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

Phase 10AI - Orchestration Graph And Performance View Initial Slice

## Phase Status

Active and ready for implementation.

## Active Task

Implement the first bounded desktop orchestration graph and performance view so
the operator can see where the loop currently is, what just completed, what is
waiting next, and where the run is blocked or halted.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify `Phase 10AI` as the active sub-phase
- `.agent-loop/phase-plan.md` records `Phase 10AI` as the active phase section
  and preserves prior phases as closed history
- `.agent-loop/claude-prompt.md` contains a scoped implementation prompt for
  the `Phase 10AI` runtime slice

## Next-Phase Gate

Do not mark this phase complete until:

- the desktop app exposes the first bounded orchestration graph or icon-based
  flow view derived from shipped canonical artifacts
- the runtime makes current phase/sub-phase/task, loop-state status,
  review/fix branch, and blocked/halted state legible to the operator
- the implementation stays canonical-artifact-first and does not invent a
  hidden graph-state store, progress cache, or second controller

## Out Of Scope For Current Phase

- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- introducing a hidden UI-only graph state store, progress cache, animation
  persistence layer, or desktop-side orchestration plane outside canonical
  artifacts
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
