# Claude Code Fix Task

## Phase
Phase 10AD - Codex-Owned Concurrent Work Initial Slice

## Objective
Fix the remaining Phase 10AD review findings in the bounded concurrent-work
slice.

## Required fixes
- Fix Issue 1 from `.agent-loop/codex-review.md`.
  Phase 10AD currently reports/gates a hypothetical concurrent-work set but
  does not actually allow any bounded Codex-owned concurrent work in a real
  production runtime path. Add a shipped runtime path that exercises the safe
  set for at least one real bounded Codex-owned action while Claude is
  implementing, and route it through the shipped
  `evaluate_codex_concurrent_work_eligibility(...)` helper first. Keep the
  fix within 10AD scope:
  - no broad/general concurrent Codex/Claude worker runtime
  - no hidden background orchestration or watcher farm
  - no mutation of Claude-owned implementation artifacts
  - no bypass of the shipped 10AB ownership contract or 10AC overlap gate
  - no widening of the Phase 10I library-callable cap
- Fix Issue 2 from `.agent-loop/codex-review.md`.
  A structural `HaltError` from `build_desktop_overlap_detection_view(...)`
  must fail closed in 10AD. The current `overlap_overall_state=None` path
  incorrectly falls through to `eligible_bounded_execution`. Update the 10AD
  view/evaluator so any structural refusal or unknown overlap evidence keeps
  the concurrent-work surface/runtime helper refused fail-closed, and add
  focused regression coverage for that exact branch.
- Update any affected README / summary text so it accurately matches the
  shipped 10AD behavior after the fixes.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 10AD scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated phases.
- Add or update focused tests for each behavior change.

## Required output
After implementing the fixes, update `.agent-loop/claude-summary.md` in the
required summary format and include the validation you ran.
