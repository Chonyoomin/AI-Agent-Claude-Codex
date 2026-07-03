# Claude Code Task

## Phase
Phase 10AB - Controlled Concurrent Operation Contract

## Objective
Implement Phase 10AB for the agent loop. This slice should define the overlap
rules, ownership boundaries, stale-artifact detection, review/fix invalidation
rules, and recovery behavior required before any concurrent Codex/Claude work
is allowed.

## Context
Implement the Controlled Concurrent Operation Contract slice for the agent
loop. This is the next mainline step after the shipped Phase 10AA memory-vault
export slice. The goal is to define the rules and refusal/recovery behavior the
system must obey before any overlapping Codex/Claude work is ever allowed.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AB as active
- `.agent-loop/phase-plan.md` records Phase 10AA as closed history and contains
  a `## Phase 10AB - Controlled Concurrent Operation Contract`
  section with concrete objective, done criteria, and exclusions
- define the overlap rules, ownership boundaries, stale-artifact detection,
  review/fix invalidation rules, and recovery behavior required before any
  concurrent Codex/Claude work is allowed
- define how overlap-safe work is distinguished from invalidating work, how
  stale prompts/reviews/fix prompts are detected, and how the loop must refuse
  or recover when overlap invalidates the active task context
- preserve approval gating, evidence review, external-workspace boundaries,
  existing run-profile semantics, and the canonical-artifact-first model
  instead of introducing hidden automation, silent mutation, or active
  background overlap
- add focused validation proving the controlled-concurrency contract is
  explicit, bounded, auditable, and fail-closed
- `README.md` reflects that Phase 10AB is active and that controlled
  concurrent-operation contract work is now the implementation focus

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
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no packaging work, hidden orchestration, or live concurrency added under the
  banner of this contract slice
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
