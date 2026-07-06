# Claude Code Fix Task

## Phase
Phase 10AC - Overlap-Safe Detection Initial Slice

## Objective
Fix the remaining Phase 10AC review findings in the overlap-detection slice.

## Required fixes
- Fix Issue 1 from `.agent-loop/codex-review.md`.
  The new overlap-detection state is only surfaced through the desktop/report
  layer today. Add a real bounded refusal path in shipped runtime code so
  Phase 10AC does more than report the signal. The fix must stay within Phase
  10AC scope:
  - no actual concurrent Codex/Claude runtime
  - no hidden background watcher
  - no Codex-owned concurrent work
  - no automatic next-phase activation
  A valid fix would be a shipped runtime gate that consults the overlap
  detection view/state at an appropriate existing operator/runtime entrypoint
  and refuses fail-closed when `overall_signal_state` is
  `refused_pending_recovery`, with focused tests proving the refusal fires.
- Fix Issue 2 from `.agent-loop/codex-review.md`.
  `_desktop_overlap_detection_derive_overall_state(...)` must fail closed when
  any required overlap evidence is unknown, not only when every signal is
  unknown. Update the aggregation logic and add focused regression coverage for
  mixed-known/mixed-unknown signal sets so the surface cannot report
  `no_signal` while some overlap evidence is unknowable.
- Update any affected README / summary text so it accurately matches the
  shipped 10AC behavior after the fixes.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 10AC scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated phases.
- Add or update focused tests for each behavior change.

## Required output
After implementing the fixes, update `.agent-loop/claude-summary.md` in the
required summary format and include the validation you ran.
