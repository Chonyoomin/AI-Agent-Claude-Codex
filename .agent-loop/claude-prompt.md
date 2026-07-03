# Claude Code Task

## Phase
Phase 10AC - Overlap-Safe Detection Initial Slice

## Objective
Implement Phase 10AC for the agent loop. This slice should implement detection
and refusal paths for unsafe overlap so the system can tell when concurrent
work would invalidate the active task context.

## Context
Implement the Overlap-Safe Detection Initial Slice for the agent loop. This is
the next mainline step after the shipped Phase 10AB controlled-concurrency
contract slice. The goal is to turn the Phase 10AB contract vocabulary into a
bounded detection and refusal layer so the system can tell when concurrent work
would invalidate the active task context, while still refusing to launch any
actual overlapping runtime.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AC as active
- `.agent-loop/phase-plan.md` records Phase 10AB as closed history and
  contains a `## Phase 10AC - Overlap-Safe Detection Initial Slice`
  section with concrete objective, done criteria, and exclusions
- implement bounded detection and refusal behavior for unsafe overlap using
  the controlled-concurrency contract defined in Phase 10AB
- distinguish overlap-safe work from invalidating work for the shipped roles
  and canonical artifacts, and surface explicit refusal or recovery behavior
  when the active context is stale or invalidated
- preserve approval gating, evidence review, external-workspace boundaries,
  existing run-profile semantics, desktop/UI boundaries, and the
  canonical-artifact-first model instead of introducing hidden automation,
  silent mutation, or active background overlap
- add focused validation proving the overlap-detection and refusal path is
  explicit, bounded, auditable, and fail-closed
- `README.md` reflects that Phase 10AC is active and that overlap-safe
  detection work is now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no actual overlapping Codex/Claude runtime, silent background orchestration,
  or hidden parallel worker model
- no Codex-owned concurrent work beyond bounded detection and refusal; that is
  deferred to Phase 10AD
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no packaging work, hidden orchestration, or live concurrency added under the
  banner of this detection slice
- no rewrite of current shipped behavior just to make future autonomy work
  easier
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
