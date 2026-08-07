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

Fix Phase C2 - Project Folder Picker And Classification Surface

## Phase Status

Active and ready for implementation.

## Active Task

Add the guided desktop folder picker and classify the selected folder as an
existing project, empty folder, partial target, or malformed target with
plain-English next-step messaging.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify `Fix Phase C2` as the active
  sub-phase
- `.agent-loop/phase-plan.md` records the Fix Phase C track and the concrete
  `Fix Phase C1` through `Fix Phase C8` slices
- `.agent-loop/claude-prompt.md` contains a scoped implementation prompt for
  the `Fix Phase C2` folder-picker and classification slice

## Next-Phase Gate

Do not mark this phase complete until:

- the desktop app lets the operator choose a project folder without terminal
  path entry
- the selected folder is classified using the shipped target inspection
  helpers as `existing_project`, `empty_folder`, `partial_target`, or
  `malformed_target`
- each classification has plain-English next-step guidance
- no UI-only target-state cache or parallel target inspection logic is added

## Out Of Scope For Current Phase

- PRD selection, run-mode selection, Start/Stop controls, or run-console work
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- introducing a hidden UI-only state store or second orchestration plane
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
