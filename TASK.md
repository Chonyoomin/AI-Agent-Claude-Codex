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

Phase 10AB - Controlled Concurrent Operation Contract

## Phase Status

Phase 10AA is complete and approved to advance. Phase 10AB is now active as
the next mainline slice focused on defining the controlled-concurrency
contract required before any overlapping Codex/Claude work is allowed.

## Active Task

Implement Phase 10AB for the agent loop. This slice should define the overlap
rules, ownership boundaries, stale-artifact detection, review/fix invalidation
rules, and recovery behavior required before any concurrent Codex/Claude work
is allowed.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AB as active
- `.agent-loop/phase-plan.md` records Phase 10AA as closed history and
  contains a `## Phase 10AB - Controlled Concurrent Operation Contract`
  section with concrete objective, done criteria, and exclusions
- the repository defines the overlap rules, ownership boundaries,
  stale-artifact detection rules, review/fix invalidation rules, and recovery
  behavior required before any concurrent Codex/Claude work is allowed
- the implementation documents how overlap-safe work is distinguished from
  invalidating work, how stale prompts/reviews/fix prompts are detected, and
  how the loop must refuse or recover when overlap invalidates the active task
  context
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, existing run-profile semantics, and the
  canonical-artifact-first model instead of introducing hidden automation,
  silent mutation, or active background overlap
- focused validation proves the controlled-concurrency contract is explicit,
  bounded, auditable, and fail-closed
- `README.md` reflects that Phase 10AB is active and that controlled
  concurrent-operation contract work is now the implementation focus

## Next-Phase Gate

Do not widen into actual concurrent Codex/Claude execution until:

- Phase 10AB receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the controlled concurrent-operation contract
- any actual overlap-safe detection or Codex-owned concurrent work is activated
  through its own later phase instead of being folded into this contract slice

## Out Of Scope For Current Phase

- any actual overlapping Codex/Claude runtime, silent background orchestration,
  or hidden parallel worker model
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any packaging work, hidden orchestration, or live concurrency added under the
  banner of this contract slice
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
