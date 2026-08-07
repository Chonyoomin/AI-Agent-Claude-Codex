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

Fix Phase C1 - First-Run Setup Contract

## Phase Status

Active and ready for implementation.

## Active Task

Define the non-technical desktop UX contract for selecting a project folder,
loading a PRD, choosing run behavior, starting/stopping the agent, and
understanding plain-English progress without terminal knowledge.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify `Fix Phase C1` as the active
  sub-phase
- `.agent-loop/phase-plan.md` records the Fix Phase C track and the concrete
  `Fix Phase C1` through `Fix Phase C8` slices
- `.agent-loop/claude-prompt.md` contains a scoped implementation prompt for
  the `Fix Phase C1` contract slice

## Next-Phase Gate

Do not mark this phase complete until:

- the repository defines a clear desktop UX contract for the single-user
  "pick a folder, load a PRD, choose run behavior, and run" workflow
- the contract defines the required setup, ready, running, waiting, blocked,
  and complete states in plain English
- the contract defines what technical details are hidden by default versus what
  is available under advanced views
- the contract is concrete enough that later Fix Phase C runtime slices can
  implement it without relying on chat context

## Out Of Scope For Current Phase

- runtime implementation of the folder picker, PRD picker, or run console
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- introducing a hidden UI-only state store or second orchestration plane
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
