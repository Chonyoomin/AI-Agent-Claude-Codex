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

Phase 10AH - Orchestration Graph And Phase-State Visualization Contract

## Phase Status

Active and ready for implementation.

## Active Task

Define the contract for a bounded desktop orchestration-visualization surface so
the app can show live loop state as a graph or icon-based flow without
inventing UI-only truth or bypassing canonical artifact ownership.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify `Phase 10AH` as the active sub-phase
- `.agent-loop/phase-plan.md` records `Phase 10AH` as the active phase section
  and preserves prior phases as closed history
- `.agent-loop/claude-prompt.md` contains a scoped implementation prompt for
  the `Phase 10AH` contract slice

## Next-Phase Gate

Do not mark this phase complete until:

- the repository defines a bounded orchestration-visualization contract for the
  desktop app
- the contract makes phase/sub-phase, current loop state, review/fix branch,
  blocked/halted states, and artifact-backed progress legible without
  inventing a second source of truth
- the contract stays bounded to reporting and visualization rather than hidden
  control or autonomous orchestration

## Out Of Scope For Current Phase

- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- introducing a hidden UI-only graph state store, progress cache, or desktop-
  side orchestration plane outside canonical artifacts
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
