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

Phase 10AF - Desktop Codex Conversation And Intervention Contract

## Phase Status

Active and ready for implementation.

## Active Task

Define the bounded desktop-side contract for an in-app Codex conversation and
intervention surface so the operator can ask Codex for reviews, fix routing,
roadmap changes, and targeted repo changes from the desktop app without
bypassing canonical artifacts, ownership rules, review evidence, or the
shipped approval and audit boundaries.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify `Phase 10AF` as the active sub-phase
- `.agent-loop/phase-plan.md` records `Phase 10AF` as the active phase section
  and preserves prior phases as closed history
- `.agent-loop/claude-prompt.md` contains a scoped implementation prompt for
  the `Phase 10AF` contract slice

## Next-Phase Gate

Do not mark this phase complete until:

- the bounded Codex conversation/intervention contract is defined in repo
  artifacts
- the contract preserves canonical-artifact-first routing and ownership
  boundaries
- implementation/runtime work for the actual desktop interaction surface
  remains deferred to a later slice

## Out Of Scope For Current Phase

- implementing the actual desktop Codex conversation runtime that belongs to
  `Phase 10AG`
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- introducing a hidden UI-only request queue, reply cache, or Codex-side state
  plane outside canonical artifacts
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
