# Claude Code Fix Task

## Objective
Fix only the issues found in `.agent-loop/codex-review.md`.

## Context
The latest implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/git-diff.patch`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

## Required fixes
- resolve the stale-attach runtime gap in Phase 10F: the repo currently ships `assert_external_target_attach_fresh(...)`, but no real production external-target runtime path invokes it, so stale-attach detection is advisory-only despite the phase plan and README claiming “the runtime refuses stale or inconsistent external-target state fail-closed”
- implement one of these coherently and update the artifacts to match:
  - preferred: wire the stale-attach assertion into an actual shipped external-target runtime path where a fail-closed stale-attach refusal is appropriate, then add focused tests proving the production path now halts with `halted_external_target_stale_attach`
  - if wiring a real production call site would violate the approved 10F scope or existing recovery semantics, then narrow the 10F README / summary / planning language so it truthfully describes the stale-attach logic as advisory-only inspector/assertion infrastructure rather than shipped runtime enforcement
- add or update focused tests so the chosen behavior is proven from the real runtime surface, not only from direct helper-function tests

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not delete files unless explicitly required and approved.
- Preserve the original task objective.
- Update tests if behavior changes.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
