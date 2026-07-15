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

Phase 10AG - Desktop Codex Conversation Surface Initial Slice

## Phase Status

Active and ready for implementation.

## Active Task

Implement the first bounded desktop-side Codex interaction surface so the
operator can compose an in-app Codex request, inspect Codex response mirrors,
and route approved Codex-owned actions through the shipped adapter/artifact
model instead of separate chat windows.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify `Phase 10AG` as the active sub-phase
- `.agent-loop/phase-plan.md` records `Phase 10AG` as the active phase section
  and preserves prior phases as closed history
- `.agent-loop/claude-prompt.md` contains a scoped implementation prompt for
  the `Phase 10AG` runtime slice

## Next-Phase Gate

Do not mark this phase complete until:

- the first bounded desktop Codex interaction surface ships and is operator-
  usable
- the runtime preserves Phase 10AF canonical-artifact-first routing,
  ownership, refusal, and audit boundaries
- the implementation stays bounded rather than widening into an autonomous
  desktop chat/orchestrator model

## Out Of Scope For Current Phase

- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- introducing a hidden UI-only request queue, reply cache, or Codex-side state
  plane outside canonical artifacts
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
