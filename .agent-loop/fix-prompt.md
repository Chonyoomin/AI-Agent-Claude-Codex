# Claude Code Fix Task

## Phase
Phase 10AC - Overlap-Safe Detection Initial Slice

## Objective
Fix the remaining Phase 10AC review finding in the overlap-detection slice.

## Required fixes
- Fix Issue 1 from `.agent-loop/codex-review.md`.
  The prior fix cycle correctly added a bounded shipped runtime refusal gate,
  but the 10AC reporter/UI/docs/tests still encode the old "detection only /
  runtime unavailable" story. Align the shipped 10AC surface with the actual
  current behavior:
  - `build_desktop_overlap_detection_view(...)` must no longer advertise
    `phase_10ac_runtime_available=False` if the shipped interpretation of that
    field is "a real 10AC runtime refusal path exists"
  - the 10AC precedence note and rendered explanatory copy must stop claiming
    that downstream refusal enforcement is deferred
  - the README 10AC paragraph must describe the shipped bounded runtime gate
    consistently from the start instead of contradicting itself
  - focused tests must be updated so they assert the corrected 10AC metadata /
    text contract
- Preserve the real scope boundary:
  - no actual overlapping Codex/Claude worker runtime
  - no hidden background watcher
  - no subprocess/network/concurrency widening
  - no change to the Phase 10I three-control library-callable cap
  - no claim that full concurrent execution ships in 10AC

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
