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

Phase 10AD - Codex-Owned Concurrent Work Initial Slice

## Phase Status

Phase 10AC is complete and approved to advance. Phase 10AD is now active as
the next mainline slice focused on enabling limited Codex-owned concurrent work
only where the shipped overlap-safe detection and ownership boundaries prove
that the work cannot invalidate Claude's active implementation context.

## Active Task

Implement Phase 10AD for the agent loop. This slice should allow bounded
Codex-owned concurrent work during Claude implementation only for explicitly
safe Codex-owned artifacts and actions that cannot invalidate the active Claude
task context under the shipped Phase 10AB/10AC rules.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AD as active
- `.agent-loop/phase-plan.md` records Phase 10AB as closed history and
  records Phase 10AC as closed history and contains a
  `## Phase 10AD - Codex-Owned Concurrent Work Initial Slice`
  section with concrete objective, done criteria, and exclusions
- the repository adds a bounded concurrent-work path for Codex-owned work that
  is provably safe under the controlled-concurrency contract defined in
  Phase 10AB and the refusal/detection behavior shipped in Phase 10AC
- the implementation distinguishes overlap-safe Codex-owned work from
  invalidating work for the shipped roles and canonical artifacts, and refuses
  or suppresses concurrent actions that would stale or invalidate Claude's
  active context
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, existing run-profile semantics, desktop/UI
  boundaries, and the canonical-artifact-first model instead of introducing
  hidden automation, silent mutation, or active background overlap
- focused validation proves the bounded Codex-owned concurrent-work path is
  explicit, auditable, ownership-safe, and fail-closed where safety cannot be
  proven
- `README.md` reflects that Phase 10AD is active and that limited safe
  Codex-owned concurrent work is now the implementation focus

## Next-Phase Gate

Do not widen into Codex-owned concurrent execution until:

- Phase 10AD receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the first bounded concurrent-work slice
- any broader or more autonomous concurrent execution is activated through a
  later dedicated phase instead of being folded into this initial safe slice

## Out Of Scope For Current Phase

- any broad concurrent Codex/Claude runtime, silent background orchestration,
  or hidden parallel worker model
- any Codex-owned concurrent work that touches Claude-owned implementation
  artifacts, changes Claude prompts/summaries, or bypasses the shipped
  overlap-safety refusal boundaries
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any packaging work, hidden orchestration, or live concurrency added under the
  banner of this bounded concurrent-work slice
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
