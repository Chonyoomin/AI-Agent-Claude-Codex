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

Phase 10AC - Overlap-Safe Detection Initial Slice

## Phase Status

Phase 10AB is complete and approved to advance. Phase 10AC is now active as
the next mainline slice focused on implementing overlap-safe detection and
refusal behavior so the system can tell when concurrent work would invalidate
the active task context.

## Active Task

Implement Phase 10AC for the agent loop. This slice should implement detection
and refusal paths for unsafe overlap so the system can tell when concurrent
work would invalidate the active task context.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AC as active
- `.agent-loop/phase-plan.md` records Phase 10AB as closed history and
  contains a `## Phase 10AC - Overlap-Safe Detection Initial Slice`
  section with concrete objective, done criteria, and exclusions
- the repository adds bounded detection and refusal behavior for unsafe overlap
  using the controlled-concurrency contract defined in Phase 10AB
- the implementation distinguishes overlap-safe work from invalidating work for
  the shipped roles and canonical artifacts, and surfaces explicit refusal or
  recovery paths when the active context is stale or invalidated
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, existing run-profile semantics, desktop/UI
  boundaries, and the canonical-artifact-first model instead of introducing
  hidden automation, silent mutation, or active background overlap
- focused validation proves the overlap-detection and refusal path is explicit,
  bounded, auditable, and fail-closed
- `README.md` reflects that Phase 10AC is active and that overlap-safe
  detection work is now the implementation focus

## Next-Phase Gate

Do not widen into Codex-owned concurrent execution until:

- Phase 10AC receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the overlap-safe detection slice
- any limited Codex-owned concurrent work is activated through Phase 10AD
  instead of being folded into this detection slice

## Out Of Scope For Current Phase

- any actual overlapping Codex/Claude runtime, silent background orchestration,
  or hidden parallel worker model
- any Codex-owned concurrent work beyond bounded detection and refusal; that is
  deferred to Phase 10AD
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any packaging work, hidden orchestration, or live concurrency added under the
  banner of this detection slice
- any rewrite of current shipped behavior just to make future autonomy work
  easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently
  ship just to simplify the implementation
- collapsing later overlap-safe detection, concurrent Codex work, packaging, or
  external sync work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the
  contract surface
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
