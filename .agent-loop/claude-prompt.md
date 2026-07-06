# Claude Code Task

## Phase
Phase 10AD - Codex-Owned Concurrent Work Initial Slice

## Objective
Implement Phase 10AD for the agent loop. This slice should allow bounded
Codex-owned concurrent work during Claude implementation only for explicitly
safe Codex-owned artifacts and actions that cannot invalidate the active Claude
task context under the shipped Phase 10AB/10AC rules.

## Context
Implement the Codex-Owned Concurrent Work Initial Slice for the agent loop.
This is the next mainline step after the shipped Phase 10AC overlap-safe
detection/refusal slice. The goal is to introduce the first bounded runtime
path where Codex can continue limited Codex-owned work while Claude is
implementing, but only when the shipped ownership boundaries and overlap-safe
detection/refusal rules prove that the work cannot invalidate Claude's active
implementation context.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AD as active
- `.agent-loop/phase-plan.md` records Phase 10AC as closed history and
  contains a `## Phase 10AD - Codex-Owned Concurrent Work Initial Slice`
  section with concrete objective, done criteria, and exclusions
- implement a bounded runtime path for limited Codex-owned concurrent work
  while Claude is implementing, but only for explicitly safe Codex-owned
  artifacts/actions whose execution is proven not to invalidate the active
  Claude context
- reuse the shipped Phase 10AB ownership boundaries and the Phase 10AC
  overlap-safe detection/refusal behavior instead of bypassing them
- ensure any attempted concurrent action outside the approved safe set is
  refused, deferred, or surfaced as ineligible rather than silently executed
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, loop-state source-of-truth rules, and the Phase 10I
  library-callable cap
- add focused validation proving the bounded concurrent-work path is explicit,
  auditable, ownership-safe, and fail-closed where safety cannot be proven
- `README.md` reflects that Phase 10AD is active and that limited safe
  Codex-owned concurrent work is now the implementation focus

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
- no broad or general-purpose overlapping Codex/Claude runtime
- no hidden background orchestration, watcher farm, or parallel worker model
- no Codex-owned concurrent work that mutates Claude-owned implementation
  artifacts, prompt/summarization artifacts, or any artifact whose mutation
  would invalidate Claude's active task context
- no bypass of the shipped Phase 10AC refusal gate or the Phase 10AB ownership
  contract
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no packaging work, hidden orchestration, or live concurrency added under the
  banner of this bounded concurrent-work slice
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
