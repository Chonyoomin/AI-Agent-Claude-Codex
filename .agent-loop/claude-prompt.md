# Claude Code Task

## Phase
Phase 10Y - Capacity Recovery And Resume Console

## Objective
Implement Phase 10Y for the agent loop. This slice should add the first desktop
capacity recovery and resume console so token or rate-limit halts, checkpoint
presence, bounded automatic-resume policy, retry or backoff state, and
operator override or resume actions are understandable without introducing a
hidden second control plane.

## Context
Implement the Capacity Recovery And Resume Console slice for the agent loop.
This is the next desktop-runtime step after the shipped Phase 10X run console.
The goal is to make token or rate-limit halts, checkpoint presence, bounded
resume policy, and operator recovery actions legible and auditable from the UI
and reporters while continuing to treat canonical artifacts as the source of
truth.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10Y as active
- `.agent-loop/phase-plan.md` records Phase 10X as closed history and contains
  a `## Phase 10Y - Capacity Recovery And Resume Console` section with
  concrete objective, done criteria, and exclusions
- add the first bounded recovery-console / resume-visibility surface to the
  shipped desktop app and related reporters
- define how token or rate-limit halt visibility, checkpoint presence, bounded
  automatic-resume policy, retry or backoff state, and operator override or
  resume actions are derived from canonical artifacts without creating hidden
  UI-only state that competes with the repo artifacts
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, checkpoint/continuation boundaries, and the Phase 10I
  library-callable cap
  instead of introducing hidden automation, silent mutation, or a parallel
  state store
- add focused validation proving the recovery-console path is bounded,
  auditable, and visibility-only with respect to orchestration state
- `README.md` reflects that Phase 10Y is active and that the capacity recovery
  / resume console is now the implementation focus

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
- no unbounded autonomy widening, hidden auto-resume behavior, or token-refresh
  polling outside shipped checkpoint/continuation semantics
- no hidden background control plane or second orchestrator that bypasses the
  shipped Python runtime
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no concurrent Codex/Claude overlap execution, model-policy extensibility, or
  hidden orchestration added under the banner of capacity recovery
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
